"""Private Windows preparation and exact-input checks; never publishes a release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from importlib import metadata
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/ocr"
BUILD = SERVICE / "build/windows"
RESOURCES = ROOT / "apps/desktop/src-tauri/resources/ocr"
FORBIDDEN = (".onnx", ".pt", ".pth", ".safetensors")
DETECTOR_SHA256 = "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fetch(record: dict, path: Path) -> None:
    """Never accept changed registry/dictionary/model bytes as a new pin."""
    if not path.exists() or digest(path) != record["sha256"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".download")
        try:
            with (
                urlopen(record["url"], timeout=120) as response,
                temporary.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
            if digest(temporary) != record["sha256"]:
                raise ValueError("Upstream checksum changed: " + path.name)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def validate_lock(record: dict) -> None:
    entries = record["packages"]
    expected = {
        line.strip()
        for line in (SERVICE / "requirements-windows-release.txt")
        .read_text()
        .splitlines()
        if line.strip() and not line.startswith("#")
    }
    actual = {e["name"] + "==" + e["version"] for e in entries}
    if expected != actual or len(entries) != len(actual):
        raise ValueError("Windows lock and input manifest differ")
    for item in entries:
        if (
            len(item["sha256"]) != 64
            or "/" in item["filename"]
            or "\\" in item["filename"]
        ):
            raise ValueError("Invalid input pin")
        if item["filename"].endswith(".whl"):
            _, python_tag, abi, target = (
                item["filename"].removesuffix(".whl").rsplit("-", 3)
            )
            compatible = (
                (python_tag == "cp311" and abi == "cp311" and target == "win_amd64")
                or (
                    python_tag in ("cp37", "cp38", "cp39", "cp310", "cp311")
                    and abi == "abi3"
                    and target == "win_amd64"
                )
                or (
                    python_tag in ("py3", "py2.py3")
                    and abi == "none"
                    and target in ("any", "win_amd64")
                )
            )
            if not compatible:
                raise ValueError(
                    "Wheel is not compatible with Windows CPython 3.11 x64: "
                    + item["filename"]
                )
    for name, version in (("torch", "2.8.0+cpu"), ("torchvision", "0.23.0+cpu")):
        entry = next(e for e in entries if e["name"] == name)
        if entry["version"] != version or not entry["url"].startswith(
            (
                "https://download.pytorch.org/whl/cpu/",
                "https://download-r2.pytorch.org/whl/cpu/",
            )
        ):
            raise ValueError("Only the pinned CPU Torch wheel is allowed")


def download_inputs() -> None:
    record = read_json(SERVICE / "windows-inputs.json")
    validate_lock(record)
    for entry in record["packages"]:
        print("Verifying pinned input: " + entry["filename"], flush=True)
        fetch(entry, BUILD / "inputs" / entry["filename"])
        if source := entry.get("source"):
            fetch(source, BUILD / "sources" / source["filename"])
    # Collecting sdists does not approve embedded BLAS/codec/compiler libraries.
    write_json(BUILD / "download-record.json", record)


def assert_no_detector(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected symlink: " + str(path))
        if path.is_file() and (
            path.suffix.lower() in FORBIDDEN
            or "comictextdetector.pt" in path.name.lower()
            or (path.stat().st_size > 10_000_000 and digest(path) == DETECTOR_SHA256)
        ):
            raise ValueError("Detector/unapproved weights in delivery: " + str(path))


def prepare_assets() -> None:
    assets = RESOURCES / "assets"
    for entry in read_json(SERVICE / "windows-assets.json"):
        target = assets / entry["path"]
        if not target.resolve().is_relative_to(assets.resolve()):
            raise ValueError("Unsafe asset path")
        fetch(entry, target)
    detector = BUILD / "detector"
    revision = "440b978563c71b758e31aaa315d100faba1efa2f"
    if not detector.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "https://github.com/dmMaze/comic-text-detector",
                str(detector),
            ],
            check=True,
        )
    subprocess.run(["git", "checkout", "--detach", revision], cwd=detector, check=True)
    if (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=detector, text=True
        ).strip()
        != revision
    ):
        raise ValueError("Detector source revision differs")
    destination = assets / "comic-text-detector"
    destination.mkdir(parents=True, exist_ok=True)
    # Copy tracked source only, with no examples, artwork, notebooks or weights.
    for relative in subprocess.check_output(
        ["git", "ls-files"], cwd=detector, text=True
    ).splitlines():
        path = Path(relative)
        if (
            path.suffix.lower() not in {".py", ".txt", ".yaml", ".yml"}
            and path.name != "LICENSE"
        ):
            continue
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(detector / path, target)
    subprocess.run(
        ["git", "apply", str(ROOT / "THIRD_PARTY_LICENSES/detector-inference.patch")],
        cwd=destination,
        check=True,
    )
    assert_no_detector(RESOURCES)


def pe_info(path: Path) -> dict:
    import pefile

    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(directories=[1, 13])
        imports = sorted(
            {
                item.dll.decode("ascii").lower()
                for group in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                for item in getattr(pe, group, [])
            }
        )
        return {"machine": hex(pe.FILE_HEADER.Machine), "imports": imports}
    finally:
        pe.close()


def native_files(directory: Path):
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                is_pe = stream.read(2) == b"MZ"
            if is_pe:
                yield path
            elif path.suffix.lower() in (".exe", ".dll", ".pyd"):
                raise ValueError("Native filename is not a PE binary: " + str(path))


def inventory_inputs() -> None:
    """Inventory the actual interpreter, wheels and frozen image independently."""
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise ValueError("Input inventory requires native Windows x64 Python")
    inputs = []
    components = []
    notices = RESOURCES / "notices"
    licenses = notices / "licenses/python"
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        version = dist.version
        copied = []
        for item in dist.files or []:
            path = Path(dist.locate_file(item))
            if not path.is_file():
                continue
            if path.name.lower().startswith(
                ("license", "licence", "copying", "notice", "copyright")
            ):
                # Preserve relative paths: wheels can contain many vendor licences.
                target = licenses / f"{name}-{version}" / str(item).replace("..", "_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                copied.append(str(target.relative_to(notices)))
            if path.suffix.lower() in (".dll", ".pyd", ".exe"):
                inputs.append(
                    {
                        "component": name + "==" + version,
                        "path": str(path),
                        "sha256": digest(path),
                        **pe_info(path),
                    }
                )
        components.append(
            {
                "id": name + "==" + version,
                "licenseMetadata": dist.metadata.get("License-Expression")
                or dist.metadata.get("License"),
                "notices": copied,
                "review": "pending",
            }
        )
    base = Path(sys.base_prefix)
    for path in native_files(base):
        # Source-built Python has PCbuild outputs; official Python has DLLs.
        if "site-packages" not in path.parts:
            inputs.append(
                {
                    "component": "CPython-" + platform.python_version(),
                    "path": str(path),
                    "sha256": digest(path),
                    **pe_info(path),
                }
            )
    frozen = RESOURCES / "runtime"
    by_hash = {}
    for item in inputs:
        by_hash.setdefault(item["sha256"], []).append(item)
    binaries = []
    for path in native_files(frozen):
        sha = digest(path)
        matches = by_hash.get(sha, [])
        binaries.append(
            {
                "path": str(path.relative_to(RESOURCES)).replace("\\", "/"),
                "sha256": sha,
                **pe_info(path),
                "buildInputs": matches,
                "review": "pending",
            }
        )
    record = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "inputManifestSha256": digest(SERVICE / "windows-inputs.json"),
        "components": components,
        "nativeInputs": inputs,
        "binaries": binaries,
        "publicDistributionApproved": False,
    }
    write_json(notices / "windows-inventory.json", record)
    write_json(BUILD / "windows-inventory.json", record)


def native_configuration() -> None:
    """Record compiled vendor versions/options for the exact Windows inputs."""
    import cv2
    import numpy
    import shapely
    import torch
    from PIL import features

    if sys.platform != "win32" or torch.version.cuda is not None:
        raise ValueError("Native configuration requires the Windows CPU environment")
    record = {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "torchCuda": torch.version.cuda,
        "torchBuild": torch.__config__.show(),
        "numpyBuild": numpy.show_config(mode="dicts"),
        "opencvBuild": cv2.getBuildInformation(),
        "geos": shapely.geos_version_string,
        "pillow": {name: features.version(name) for name in features.get_supported()},
        "inputManifestSha256": digest(SERVICE / "windows-inputs.json"),
        "publicDistributionApproved": False,
    }
    write_json(BUILD / "windows-native-configuration.json", record)
    write_json(RESOURCES / "notices/windows-native-configuration.json", record)


def seal_resources(resources: Path) -> None:
    """Bind Python archives, data and notices as well as native binaries."""
    manifest = resources / "notices/windows-resource-hashes.json"
    files = {
        p.relative_to(resources).as_posix(): digest(p)
        for p in sorted(resources.rglob("*"))
        if p.is_file() and p != manifest
    }
    write_json(manifest, files)


def verify_resources(resources: Path) -> dict:
    assert_no_detector(resources)
    required = [
        "LICENSE",
        "MODEL_CREDITS.md",
        "ASSET_NOTICES.md",
        "windows-inventory.json",
        "project-revision.txt",
        "windows-inputs.json",
        "windows-assets.json",
        "distribution.json",
        "windows-resource-hashes.json",
    ]
    for name in required:
        if not (resources / "notices" / name).is_file():
            raise ValueError("Missing Windows notice/record: " + name)
    if not (resources / "runtime/yomimado-ocr.exe").is_file():
        raise ValueError("Missing Windows frozen executable")
    manifest = resources / "notices/windows-resource-hashes.json"
    actual_files = {
        p.relative_to(resources).as_posix(): digest(p)
        for p in sorted(resources.rglob("*"))
        if p.is_file() and p != manifest
    }
    if actual_files != read_json(manifest):
        raise ValueError("Installed resource hashes differ")
    for name in ("windows-inputs.json", "windows-assets.json"):
        if digest(resources / "notices" / name) != digest(SERVICE / name):
            raise ValueError("Installed input manifest differs: " + name)
    for entry in read_json(SERVICE / "windows-assets.json"):
        if digest(resources / "assets" / entry["path"]) != entry["sha256"]:
            raise ValueError("Installed asset changed: " + entry["path"])
    inventory = read_json(resources / "notices/windows-inventory.json")
    expected = {b["path"]: b["sha256"] for b in inventory["binaries"]}
    actual = {}
    for path in native_files(resources / "runtime"):
        info = pe_info(path)
        if info["machine"] != "0x8664":
            raise ValueError("Mixed/unsupported architecture: " + str(path))
        actual[str(path.relative_to(resources)).replace("\\", "/")] = digest(path)
    if not actual or actual != expected:
        raise ValueError("Installed native inventory differs")
    if any("cuda" in name.lower() or "cudnn" in name.lower() for name in actual):
        raise ValueError("CUDA binary in CPU candidate")
    bundled = {p.name.lower() for p in native_files(resources / "runtime")}
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    for entry in inventory["binaries"]:
        for name in entry["imports"]:
            if name in bundled or name.startswith(("api-ms-win-", "ext-ms-win-")):
                continue
            # VC runtimes must be app-local; a developer runner having them in
            # System32 is not evidence that a clean user's PC will have them.
            if (
                name.startswith(
                    (
                        "vcruntime",
                        "msvcp",
                        "vcomp",
                        "concrt",
                        "libiomp",
                        "mkl",
                        "cuda",
                        "cudnn",
                    )
                )
                or not (system / name).is_file()
            ):
                raise ValueError("Missing app-local native dependency: " + name)
    return inventory


def package(installer: Path, output: Path, installed: Path) -> None:
    verify_resources(installed / "ocr")
    if pe_info(installed / "yomimado.exe")["machine"] != "0x8664":
        raise ValueError("Desktop executable is not x64")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("Candidate must be built from a clean source tree")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if (installed / "ocr/notices/project-revision.txt").read_text().strip() != revision:
        raise ValueError("Installed source revision mismatch")
    from windows_notices import installer_inputs

    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "windows-installer-inputs.json", installer_inputs(installed, installer)
    )
    shutil.copy2(installer, output / installer.name)
    with tarfile.open(output / "windows-notices.tar.gz", "w:gz") as archive:
        archive.add(installed / "ocr/notices", arcname="notices")
    # This is a private worksheet/source collection, not an approved GPL delivery.
    source = output / "windows-source-preparation.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(BUILD / "sources", arcname="sources")
        for path in (
            ROOT / "scripts/build-windows-prerelease.ps1",
            ROOT / "scripts/windows_release.py",
            SERVICE / "windows-inputs.json",
            ROOT / "scripts/windows_python.py",
            ROOT / "scripts/windows_notices.py",
        ):
            archive.add(path, arcname="recipes/" + path.name)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            f"--output={output / 'project-sources.tar.gz'}",
            revision,
        ],
        cwd=ROOT,
        check=True,
    )
    assets = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    record = {
        "mode": "private-test",
        "platform": "windows-x64",
        "sourceRevision": revision,
        "installedAppVerified": False,
        "publicDistributionApproved": False,
        "assets": assets,
    }
    write_json(output / "windows-candidate.json", record)
    (output / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha}  {name}\n"
            for name, sha in {
                **assets,
                "windows-candidate.json": digest(output / "windows-candidate.json"),
            }.items()
        ),
        encoding="utf-8",
    )
    print(json.dumps(record))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "download",
            "assets",
            "inventory",
            "configuration",
            "seal",
            "verify",
            "package",
        ],
    )
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    parser.add_argument("--installed", type=Path)
    parser.add_argument("--installer", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "download":
        download_inputs()
    elif args.command == "assets":
        prepare_assets()
    elif args.command == "inventory":
        inventory_inputs()
    elif args.command == "configuration":
        native_configuration()
    elif args.command == "seal":
        seal_resources(args.resources)
    elif args.command == "verify":
        verify_resources(args.resources)
    else:
        package(args.installer, args.output, args.installed)


if __name__ == "__main__":
    main()
