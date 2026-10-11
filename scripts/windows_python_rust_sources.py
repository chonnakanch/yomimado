"""Retain original locked Rust dependencies of the four Windows Python wheels."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath

import tomllib
from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    SERVICE,
    digest,
    fetch,
    read_json,
    write_json,
)

PACKAGES = {"pydantic_core", "safetensors", "tokenizers", "watchfiles"}


def regular_members(archive: tarfile.TarFile):
    seen = set()
    for item in archive.getmembers():
        path = PurePosixPath(item.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in item.name
            or item.name in seen
        ):
            raise ValueError("Unsafe Rust preferred-source archive member")
        seen.add(item.name)
        if item.isdir():
            continue
        if not item.isfile():
            raise ValueError("Non-regular Rust preferred-source archive member")
        yield item


def locked_sources(archive: Path) -> tuple[dict, list[dict]]:
    with tarfile.open(archive) as source:
        members = list(regular_members(source))
        locks = [
            item for item in members if PurePosixPath(item.name).name == "Cargo.lock"
        ]
        if len(locks) != 1:
            raise ValueError("Exactly one original Python Rust lock is required")
        raw = source.extractfile(locks[0]).read()
        lock = tomllib.loads(raw.decode("utf-8"))
        entries = []
        for package in lock["package"]:
            if not package.get("source"):
                continue
            if (
                package["source"]
                != "registry+https://github.com/rust-lang/crates.io-index"
            ):
                raise ValueError("Unretained non-registry Python Rust dependency")
            sha = package.get("checksum", "")
            if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("Missing original Python Rust checksum")
            name, version = package["name"], package["version"]
            if any(c in name + version for c in "/\\:"):
                raise ValueError("Unsafe Python Rust package identity")
            entries.append({"name": name, "version": version, "sha256": sha})
        if not entries:
            raise ValueError("Empty Python Rust dependency lock")
        return {
            "path": locks[0].name,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }, entries


def collect() -> None:
    pins = read_json(SERVICE / "windows-inputs.json")
    destination = BUILD / "sources/python-rust"
    notices = RESOURCES / "notices/python-rust"
    destination.mkdir(parents=True, exist_ok=True)
    notices.mkdir(parents=True, exist_ok=True)
    originals, crates = {}, {}
    for package in pins["packages"]:
        if package["name"] not in PACKAGES:
            continue
        original = BUILD / "sources" / package["source"]["filename"]
        fetch(package["source"], original)
        lock, entries = locked_sources(original)
        originals[package["name"]] = {
            "version": package["version"],
            "wheelSha256": package["sha256"],
            "sourceSha256": digest(original),
            "lock": lock,
            "dependencies": entries,
        }
        for entry in entries:
            key = entry["name"] + "-" + entry["version"]
            if key in crates and crates[key]["sha256"] != entry["sha256"]:
                raise ValueError("Conflicting Python Rust original checksum")
            crates[key] = entry
    if set(originals) != PACKAGES:
        raise ValueError("Incomplete Python Rust source inputs")
    notice_records = {}
    supplements = {
        entry["crate"]: entry
        for entry in read_json(ROOT / "docs/windows-python-rust-notice-inputs.json")
    }
    for key, entry in sorted(crates.items()):
        path = destination / (key + ".crate")
        fetch(
            {
                **entry,
                "url": f"https://static.crates.io/crates/{entry['name']}/{key}.crate",
            },
            path,
        )
        texts = {}
        with tarfile.open(path) as source:
            members = list(regular_members(source))
            manifests = [m for m in members if m.name == key + "/Cargo.toml"]
            if len(manifests) != 1:
                raise ValueError("Missing original Rust package manifest: " + key)
            manifest = tomllib.loads(
                source.extractfile(manifests[0]).read().decode("utf-8")
            )["package"]
            if (
                manifest["name"] != entry["name"]
                or manifest["version"] != entry["version"]
            ):
                raise ValueError("Rust original package identity differs")
            for item in members:
                if (
                    not PurePosixPath(item.name)
                    .name.lower()
                    .startswith(
                        (
                            "license",
                            "licence",
                            "copying",
                            "notice",
                            "copyright",
                            "authors",
                        )
                    )
                ):
                    continue
                relative = PurePosixPath(item.name)
                if relative.parts[0] != key:
                    raise ValueError("Rust notice escapes its package root")
                raw = source.extractfile(item).read()
                target = notices.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                texts[relative.as_posix()] = hashlib.sha256(raw).hexdigest()
            if supplement := supplements.get(key):
                vcs_member = next(
                    m for m in members if m.name == key + "/.cargo_vcs_info.json"
                )
                vcs = json.loads(source.extractfile(vcs_member).read())
                if (
                    digest(path) != supplement["crateSha256"]
                    or manifest["repository"] != supplement["repository"]
                    or vcs["git"]["sha1"] != supplement["revision"]
                ):
                    raise ValueError(
                        "Rust supplemental notice original revision differs"
                    )
                for pin in supplement["files"]:
                    relative = key + "/upstream/" + pin["filename"]
                    if Path(pin["filename"]).name != pin["filename"]:
                        raise ValueError("Unsafe Rust supplemental notice path")
                    retained = destination / "supplements" / relative
                    fetch(pin, retained)
                    target = notices / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(retained.read_bytes())
                    texts[relative] = digest(retained)
            if not texts:
                raise ValueError("Missing full original Rust notice: " + key)
            notice_records[key] = {
                "originalSha256": digest(path),
                "licenseExpression": manifest.get("license"),
                "notices": texts,
            }
    record = {
        "packages": originals,
        "crates": notice_records,
        "recipeSha256": digest(Path(__file__)),
        "supplementManifestSha256": digest(
            ROOT / "docs/windows-python-rust-notice-inputs.json"
        ),
        "supplements": list(supplements.values()),
        "scope": "Complete original Cargo.lock dependencies, including optional and non-Windows targets; no binary rebuild attestation",
        "sourceCoverageApproved": False,
        "publicDistributionApproved": False,
    }
    for directory in (destination, notices):
        write_json(directory / "source-preparation.json", record)
        (directory / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
        (directory / "windows-python-rust-notice-inputs.json").write_bytes(
            (ROOT / "docs/windows-python-rust-notice-inputs.json").read_bytes()
        )
        (directory / "README.md").write_text(
            "# Python Rust preferred sources\n\nThe parent source archive contains the original wheel sdists and their Cargo.lock files. This directory retains every registry crate in those exact locks. To prepare an offline build, extract a parent sdist and use `cargo vendor --locked` with these original archives in Cargo's registry cache, then build its documented Python binding with the recorded Windows toolchain. Optional/non-Windows entries are retained to avoid claiming a narrower wheel build graph. No source rebuild or public approval is claimed.\n",
            encoding="utf-8",
        )
    print(f"Retained {len(crates)} original Python Rust crates and notices")


if __name__ == "__main__":
    collect()
