"""Stage only unchanged, hash-pinned canonical VC runtime files for private tests."""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    digest,
    native_files,
    pe_info,
    read_json,
    write_json,
)

MANIFEST = ROOT / "docs/windows-vc-runtime-inputs.json"
RECORD = "windows-vc-replacement.json"


def vc_name(filename: str, allowed: dict) -> str | None:
    name = filename.lower()
    if not name.startswith(("msvcp140", "vcruntime140", "concrt140", "vccorlib140")):
        return None
    name = re.sub(r"-[0-9a-f]{32}(?=\.dll$)", "", name)
    if name not in allowed:
        raise ValueError("Unreviewed VC runtime name: " + filename)
    return name


def stage(resources: Path = RESOURCES) -> None:
    manifest = read_json(MANIFEST)
    vs = os.environ.get("VSINSTALLDIR")
    if not vs:
        raise ValueError("Selected Visual Studio directory is unavailable")
    originals = Path(vs) / "VC/Redist/MSVC" / manifest["redistDirectory"]
    allowed = manifest["files"]
    # Validate all originals before modifying the task-owned frozen runtime.
    infos = {}
    for name, sha in allowed.items():
        source = originals / name
        if digest(source) != sha:
            raise ValueError("Canonical VC runtime hash differs: " + name)
        infos[name] = pe_info(source)
        if infos[name]["machine"] != "0x8664":
            raise ValueError("Canonical VC runtime is not AMD64")
    runtime = resources / "runtime"
    targets = {}
    for path in native_files(runtime):
        name = vc_name(path.name, allowed)
        if name:
            targets[path] = name
    if not targets:
        raise ValueError("No frozen VC runtime inputs found")
    # Retain renamed import names without modifying Microsoft's PE bytes.
    # Include any normal or delay-loaded VC dependency of the new originals.
    needed = set(targets.values())
    while True:
        dependencies = {
            name
            for item in needed
            for dependency in infos[item]["imports"]
            if (name := vc_name(dependency, allowed)) is not None
        }
        existing = {str(path).lower() for path in targets}
        for name in dependencies:
            target = runtime / "_internal" / name
            if str(target).lower() not in existing:
                targets[target] = name
        more = dependencies - needed
        if not more:
            break
        needed.update(more)
    records = []
    for target, name in sorted(targets.items()):
        original_sha = digest(target) if target.is_file() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(originals / name, target)
        records.append(
            {
                "destination": target.relative_to(resources).as_posix(),
                "originalFrozenSha256": original_sha,
                "component": "Microsoft-VC143-CRT-" + manifest["version"],
                "path": str((originals / name).resolve()),
                "sha256": allowed[name],
                **infos[name],
            }
        )
    record = {
        "manifestSha256": digest(MANIFEST),
        "recipeSha256": digest(Path(__file__)),
        "files": records,
        "licensedDistributorConfirmed": False,
        "publicDistributionApproved": False,
    }
    notices = resources / "notices"
    write_json(BUILD / RECORD, record)
    write_json(notices / RECORD, record)
    for path in (MANIFEST, Path(__file__)):
        shutil.copy2(path, notices / path.name)
    bound_inputs(resources, check_sources=True)
    print(
        "Staged unchanged canonical VC runtimes; redistribution approval remains open."
    )


def bound_inputs(resources: Path, *, check_sources: bool = False) -> list[dict]:
    notices = resources / "notices"
    manifest_path = notices / MANIFEST.name
    manifest = read_json(manifest_path)
    record = read_json(notices / RECORD)
    if (
        record["manifestSha256"] != digest(manifest_path)
        or record["manifestSha256"] != digest(MANIFEST)
        or record["recipeSha256"] != digest(notices / Path(__file__).name)
        or record["recipeSha256"] != digest(Path(__file__))
    ):
        raise ValueError("VC runtime replacement record differs")
    expected = {}
    for item in record["files"]:
        relative = item["destination"]
        path = Path(relative)
        if (
            not relative.startswith("runtime/_internal/")
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in relative
            or ":" in relative
            or relative.lower() in expected
        ):
            raise ValueError("Unsafe or duplicate VC runtime destination")
        name = vc_name(path.name, manifest["files"])
        if check_sources:
            vs = os.environ.get("VSINSTALLDIR")
            if not vs or name is None:
                raise ValueError("Canonical VC source directory is unavailable")
            canonical = Path(vs) / "VC/Redist/MSVC" / manifest["redistDirectory"] / name
            if Path(item["path"]).resolve() != canonical.resolve():
                raise ValueError("VC input is outside the selected canonical directory")
        if (
            name is None
            or item["sha256"] != manifest["files"][name]
            or item["machine"] != "0x8664"
            or digest(resources / path) != item["sha256"]
            or (check_sources and digest(Path(item["path"])) != item["sha256"])
        ):
            raise ValueError("VC runtime input is unbound")
        expected[relative.lower()] = item
    actual = {
        path.relative_to(resources).as_posix().lower()
        for path in native_files(resources / "runtime")
        if vc_name(path.name, manifest["files"])
    }
    if not expected or actual != set(expected):
        raise ValueError("VC replacement does not cover actual frozen files")
    return list(expected.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage",))
    args = parser.parse_args()
    stage()
