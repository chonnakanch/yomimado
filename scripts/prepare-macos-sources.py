"""Gather checksum-verified source candidates; never approve a source delivery.

Run with the OCR build Python (tomli is pinned in that environment). Downloads
are data only: no archive extraction, setup.py execution or package installation.
The separate release validator still requires complete source/notice review.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

import tomli

ROOT = Path(__file__).resolve().parents[1]
CARGO_CACHE = Path.home() / ".cargo/registry/cache"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def checked_url(url: str, hosts: set[str]) -> str:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in hosts
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Source URL must use the expected HTTPS registry")
    return url


def filename(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.+-]+", value) or value in {".", ".."}:
        raise ValueError("Unsafe source filename")
    return value


def download(url: str, target: Path, expected: str, algorithm: str, hosts: set[str]):
    checked_url(url, hosts)
    if target.exists():
        if digest(target, algorithm) != expected:
            raise ValueError(f"Cached source checksum mismatch: {target.name}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            checked_url(response.geturl(), hosts)
            with partial.open("wb") as output:
                size = 0
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > 512 * 1024 * 1024:
                        raise ValueError("Source archive exceeds 512 MiB")
                    output.write(block)
        if digest(partial, algorithm) != expected:
            raise ValueError(f"Downloaded source checksum mismatch: {target.name}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def validate_vendor(vendor: Path, lock: Path) -> dict[tuple[str, str], Path]:
    packages = tomli.loads(lock.read_text())["package"]
    locked = {
        (item["name"], item["version"]): item["checksum"]
        for item in packages
        if item.get("source", "").startswith("registry+")
    }
    found = {}
    for directory in sorted(vendor.iterdir()):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Unexpected file/symlink in Cargo vendor tree")
        manifest = tomli.loads((directory / "Cargo.toml").read_text())["package"]
        key = (manifest["name"], manifest["version"])
        record = json.loads((directory / ".cargo-checksum.json").read_text())
        if key in found or record["package"] != locked.get(key):
            raise ValueError(f"Cargo package does not match lockfile: {key}")
        files = record["files"]
        # A modified vendor tree could forge its own per-file checksum map.
        # Bind that map to the original .crate archive and Cargo.lock digest.
        archives = list(CARGO_CACHE.glob(f"*/{key[0]}-{key[1]}.crate"))
        archive = next((path for path in archives if digest(path) == locked[key]), None)
        if archive is None:
            raise ValueError(f"Missing checksum-verified original Cargo archive: {key}")
        original = {}
        with tarfile.open(archive, "r:gz") as bundle:
            prefix = f"{key[0]}-{key[1]}/"
            for member in bundle.getmembers():
                if member.isdir():
                    continue
                if not member.isfile() or not member.name.startswith(prefix):
                    raise ValueError("Unexpected entry in original Cargo archive")
                relative = member.name[len(prefix) :]
                with bundle.extractfile(member) as stream:
                    original[relative] = hashlib.sha256(stream.read()).hexdigest()
        if any(
            original.get(relative) != checksum for relative, checksum in files.items()
        ):
            raise ValueError(
                f"Cargo vendor map differs from original source archive: {key}"
            )
        actual = set()
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symlink in Cargo vendor sources")
            if path.is_file():
                relative = path.relative_to(directory).as_posix()
                if relative != ".cargo-checksum.json":
                    actual.add(relative)
        if actual != set(files):
            raise ValueError(f"Cargo source file coverage mismatch: {key}")
        for relative, expected in files.items():
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError("Cargo checksum path escapes source directory")
            if digest(path) != expected:
                raise ValueError(f"Cargo source checksum mismatch: {key}: {relative}")
        found[key] = directory
    if set(found) != set(locked):
        raise ValueError("Cargo vendor tree does not cover the full lockfile")
    return found


def cargo_archive(vendor: Path, output: Path, components: list[dict]) -> list[dict]:
    if output.is_relative_to(vendor):
        raise ValueError("Source output must be outside the Cargo vendor tree")
    lock = ROOT / "apps/desktop/src-tauri/Cargo.lock"
    found = validate_vendor(vendor, lock)
    rust = [item for item in components if item["ecosystem"] == "rust"]
    if any((item["name"], item["version"]) not in found for item in rust):
        raise ValueError("Cargo vendor sources do not cover the bundled inventory")
    build = output / "CARGO-BUILD.md"
    build.write_text(
        "# Locked Rust source candidates\n\n"
        "This archive preserves every registry crate in Cargo.lock, including\n"
        "non-macOS targets. All crate file and package checksums were checked\n"
        "against original .crate archives, which are also included in full.\n"
        "Cargo vendor can omit VCS metadata from its extracted directories.\n"
        "It is dependency source only; YomiMado source/build scripts, native\n"
        "wheel sources and final notice review are separate requirements.\n\n"
        "Extract beside the matching project checkout. Configure .cargo/config.toml:\n\n"
        "```toml\n[source.crates-io]\nreplace-with = 'vendored-sources'\n"
        "[source.vendored-sources]\ndirectory = 'vendor'\n```\n\n"
        "Build with the project's locked Rust/Tauri toolchain and npm/Python\n"
        "inputs using scripts/build-macos-prerelease.sh. Publisher credentials\n"
        "are unnecessary for a private build. Source/license review is pending.\n"
    )
    archive = output / "cargo-sources.tar.gz"
    temporary = archive.with_suffix(".part")
    try:
        with tarfile.open(temporary, "w:gz") as bundle:
            bundle.add(vendor, arcname="vendor")
            bundle.add(lock, arcname="Cargo.lock")
            bundle.add(build, arcname="CARGO-BUILD.md")
            for key, directory in sorted(found.items()):
                checksum = json.loads((directory / ".cargo-checksum.json").read_text())[
                    "package"
                ]
                archive_name = f"{key[0]}-{key[1]}.crate"
                original = next(
                    path
                    for path in CARGO_CACHE.glob(f"*/{archive_name}")
                    if digest(path) == checksum
                )
                bundle.add(original, arcname="original-crates/" + archive_name)
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
    checksum = digest(archive)
    return [
        candidate(
            item, archive, output, checksum, "Cargo.lock + verified vendor checksums"
        )
        for item in rust
    ]


def candidate(item: dict, path: Path, output: Path, checksum: str, origin: str) -> dict:
    return {
        "id": f"{item['ecosystem']}:{item['name']}@{item['version']}",
        "archive": path.relative_to(output).as_posix(),
        "sha256": checksum,
        "origin": origin,
        "status": "source-candidate-review-pending",
    }


def python_archive(item: dict, output: Path) -> dict:
    if item["name"].lower() == "opencv-python":
        path = ROOT / "services/ocr/build/opencv-source/opencv-source-delivery.tar.gz"
        expected = "b426f96f5620aa310dd0971d0a247e5b0d81f880412aed43d665f141f9fd3f12"
        if digest(path) != expected:
            raise ValueError("OpenCV source delivery differs from reviewed input")
        target = output / path.name
        shutil.copyfile(path, target)
        return candidate(
            item, target, output, expected, "custom OpenCV source/build record"
        )
    name, version = item["name"], item["version"]
    url = f"https://pypi.org/pypi/{urllib.parse.quote(name, safe='')}/{urllib.parse.quote(version, safe='')}/json"
    with urllib.request.urlopen(url, timeout=60) as response:
        checked_url(response.geturl(), {"pypi.org"})
        data = json.loads(response.read(8 * 1024 * 1024))
    normalized = lambda value: re.sub(r"[-_.]+", "-", value).lower()
    if (
        normalized(data["info"]["name"]) != normalized(name)
        or data["info"]["version"] != version
    ):
        raise ValueError("PyPI source metadata name/version mismatch")
    sources = [
        entry
        for entry in data["urls"]
        if entry["packagetype"] == "sdist" and not entry["yanked"]
    ]
    if len(sources) != 1:
        raise ValueError(
            "Exact release has no unique unyanked PyPI source distribution"
        )
    source = sources[0]
    path = output / "python" / filename(source["filename"])
    checksum = source["digests"]["sha256"]
    download(source["url"], path, checksum, "sha256", {"files.pythonhosted.org"})
    return candidate(item, path, output, checksum, source["url"])


def javascript_archive(item: dict, output: Path) -> dict:
    lock = json.loads((ROOT / "apps/desktop/package-lock.json").read_text())
    entry = lock["packages"]["node_modules/" + item["name"]]
    if entry["version"] != item["version"]:
        raise ValueError("npm source version differs from inventory")
    algorithm, encoded = entry["integrity"].split("-", 1)
    if algorithm != "sha512":
        raise ValueError("npm source requires locked SHA-512 integrity")
    expected = base64.b64decode(encoded, validate=True).hex()
    if len(expected) != 128:
        raise ValueError("Invalid npm integrity digest")
    path = (
        output
        / "javascript"
        / filename(
            item["name"].replace("@", "").replace("/", "-")
            + "-"
            + item["version"]
            + ".tgz"
        )
    )
    download(entry["resolved"], path, expected, algorithm, {"registry.npmjs.org"})
    return candidate(item, path, output, digest(path), entry["resolved"])


def export_git_sources(
    checkout: Path,
    output: Path,
    name: str,
    revision: str,
    omitted: list[str] | None = None,
) -> Path:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Source export requires an exact Git commit")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout):
        raise ValueError("Source checkout must be clean before export")
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision], cwd=checkout, text=True
    ).splitlines()
    selected = [path for path in tracked if path not in (omitted or [])]
    if not selected:
        raise ValueError("Source export would contain no approved files")
    target = output / filename(name + "-" + revision + ".tar.gz")
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            "--prefix=" + name + "/",
            "--output=" + str(target),
            revision,
            "--",
            *selected,
        ],
        cwd=checkout,
        check=True,
    )
    return target


def excluded_detector_path(value: str) -> bool:
    return value.startswith(("data/doc/", "data/examples/")) or Path(
        value
    ).suffix.lower() in {
        ".onnx",
        ".pt",
        ".pth",
        ".ipynb",
        ".ttf",
        ".otf",
        ".ttc",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
    }


def detector_archive(item: dict, output: Path) -> dict:
    if item["name"] != "comic-text-detector":
        raise ValueError("No reviewed export filter for this source component")
    checkout = ROOT / "services/ocr/local-models/comic-text-detector"
    revision = item["version"]
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision], cwd=checkout, text=True
    ).splitlines()
    omitted = [path for path in tracked if excluded_detector_path(path)]
    path = export_git_sources(
        checkout, output, "comic-text-detector", revision, omitted
    )
    omissions = {
        "revision": revision,
        "omitted": omitted,
        "reason": "Unneeded example artwork/fonts, notebooks and model weights are excluded; source code is unchanged.",
    }
    (output / "detector-source-omissions.json").write_text(
        json.dumps(omissions, indent=2) + "\n"
    )
    record = candidate(item, path, output, digest(path), "git:" + revision)
    record["omissionsRecord"] = "detector-source-omissions.json"
    record["omissionsSha256"] = digest(output / "detector-source-omissions.json")
    return record


def apply_native_reviews(
    notices: Path, output: Path, binaries: list[dict], report: dict, review_path: Path
) -> set[str]:
    """Reuse explicit, hash-bound technical reviews without approving a release."""
    if not review_path.exists():
        return set()
    reviews = json.loads(review_path.read_text())
    inputs = {item["id"]: item for item in binaries if not item.get("aliasOf")}
    reviewed = set()
    for group in reviews["groups"]:
        archive = (output / group["archive"]).resolve()
        if (
            not archive.is_relative_to(output.resolve())
            or digest(archive) != group["sha256"]
        ):
            raise ValueError("Reviewed native source archive differs from evidence")
        if not group.get("licenseEvidence") or not group.get("noticeFiles"):
            raise ValueError("Native review lacks licence/notice evidence")
        for relative, expected in group["noticeFiles"].items():
            path = (notices / relative).resolve()
            if not path.is_relative_to(notices.resolve()) or digest(path) != expected:
                raise ValueError("Reviewed native notice differs from evidence")
        for entry in group["nativeInputs"]:
            key = entry["id"]
            if (
                key in reviewed
                or key not in inputs
                or inputs[key]["buildInputSha256"] != entry["buildInputSha256"]
            ):
                raise ValueError("Reviewed native input differs from evidence")
            reviewed.add(key)
            report["candidates"].append(
                {
                    "id": key,
                    "archive": group["archive"],
                    "sha256": group["sha256"],
                    "origin": group["licenseEvidence"],
                    "status": "source-and-notice-evidence-verified",
                    "noticeFiles": list(group["noticeFiles"]),
                    "buildInputSha256": entry["buildInputSha256"],
                }
            )
    report["nativeReviewRecordSha256"] = digest(review_path)
    report["nativeEvidenceVerified"] = len(reviewed)
    return reviewed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notices", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cargo-vendor", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifests = ("third-party-manifest.json", "native-libraries.json")
    components = json.loads((args.notices / manifests[0]).read_text())["components"]
    report = {
        "status": "unreviewed-source-candidates-not-release-delivery",
        "inventorySha256": {name: digest(args.notices / name) for name in manifests},
        "candidates": cargo_archive(args.cargo_vendor.resolve(), output, components),
        "unresolved": [],
    }
    for item in components:
        if item["ecosystem"] not in {"python", "javascript"}:
            continue
        key = f"{item['ecosystem']}:{item['name']}@{item['version']}"
        try:
            record = (
                python_archive if item["ecosystem"] == "python" else javascript_archive
            )(item, output)
            report["candidates"].append(record)
            print("Collected " + key, flush=True)
        except (ValueError, OSError, KeyError) as error:
            report["unresolved"].append({"id": key, "reason": str(error)})
            print("Unresolved " + key + ": " + str(error), flush=True)
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        path = export_git_sources(ROOT, output, "yomimado", revision)
        report["projectRevision"] = revision
        report["candidates"].append(
            {
                "id": "project:yomimado",
                "archive": path.name,
                "sha256": digest(path),
                "origin": "git:" + revision,
                "status": "source-candidate-review-pending",
            }
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        report["unresolved"].append({"id": "project:yomimado", "reason": str(error)})
    for item in components:
        if item["ecosystem"] == "source":
            try:
                if item["name"] in {"CPython", "OpenSSL", "liblzma"}:
                    path = (
                        ROOT
                        / "services/ocr/build/python-source/python-source-delivery.tar.gz"
                    )
                    target = output / path.name
                    shutil.copyfile(path, target)
                    report["candidates"].append(
                        candidate(
                            item,
                            target,
                            output,
                            digest(target),
                            "pinned Python/OpenSSL/liblzma build record and original archives",
                        )
                    )
                else:
                    report["candidates"].append(detector_archive(item, output))
            except (ValueError, OSError, subprocess.CalledProcessError) as error:
                report["unresolved"].append(
                    {
                        "id": f"source:{item['name']}@{item['version']}",
                        "reason": str(error),
                    }
                )
    binaries = json.loads((args.notices / manifests[1]).read_text())["binaries"]
    reviewed = apply_native_reviews(
        args.notices,
        output,
        binaries,
        report,
        ROOT / "THIRD_PARTY_LICENSES/macos-native-review.json",
    )
    for binary in binaries:
        if not binary.get("aliasOf") and binary["id"] not in reviewed:
            report["unresolved"].append(
                {
                    "id": binary["id"],
                    "reason": "Exact native source, patches/build recipe and applicable notices need review",
                }
            )
    (output / "source-candidates.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Source candidates: {len(report['candidates'])}; unresolved: {len(report['unresolved'])}. No release approval recorded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
