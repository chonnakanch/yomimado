"""Install the audited IPP-free OpenCV build into the private Windows runtime."""

from __future__ import annotations

import argparse
import importlib.metadata
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    digest,
    pe_info,
    read_json,
    write_json,
)

AUDIT = ROOT / "services/ocr/build/windows-opencv-audit"


def verified_build() -> tuple[dict, Path]:
    record = read_json(AUDIT / "build-verification.json")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if (
        record.get("passed") is not True
        or record.get("commit") != revision
        or record.get("inputs")
        != read_json(ROOT / "docs/windows-opencv-build-inputs.json")
        or record.get("recipeSha256")
        != digest(ROOT / "scripts/build-opencv-windows.py")
        or record.get("probeSha256") != digest(ROOT / "scripts/opencv-windows-probe.py")
        or "-DWITH_IPP=OFF" not in record.get("options", [])
        or "-DBUILD_WITH_STATIC_CRT=OFF" not in record.get("options", [])
        or record.get("releaseDllRuntimeCompileCommands", 0) <= 0
        or record.get("cmakeCacheSha256") != digest(AUDIT / "CMakeCache.txt")
        or record.get("compileCommandsSha256")
        != digest(AUDIT / "compile_commands.json")
    ):
        raise ValueError("Unbound or incomplete IPP-free OpenCV build")
    binaries = list((AUDIT / "cmake-build").rglob("cv2*.pyd"))
    if len(binaries) != 1:
        raise ValueError("Expected exactly one source-built OpenCV extension")
    binary = binaries[0]
    if (
        digest(binary) != record["native"]["sha256"]
        or pe_info(binary)["machine"] != "0x8664"
    ):
        raise ValueError("Source-built OpenCV extension differs")
    return record, binary


def replace() -> None:
    record, binary = verified_build()
    package = Path(importlib.metadata.distribution("opencv-python").locate_file("cv2"))
    original = list(package.glob("cv2*.pyd"))
    if len(original) != 1:
        raise ValueError("Expected exactly one original OpenCV wheel extension")
    # Import the extension directly, as in the audited native/frozen probe.
    # The wheel's wrapper imports G-API bindings excluded from this focused build.
    # Preserve original notices at their metadata paths, but remove that wrapper
    # and its unused native inputs; an empty namespace directory cannot shadow PYD.
    old_hash = digest(original[0])
    notices = {
        path.relative_to(package): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
        and path.name.lower().startswith(
            ("license", "licence", "copying", "notice", "copyright")
        )
    }
    wrapper_hashes = {
        str(path.relative_to(package)): digest(path) for path in package.rglob("*.py")
    }
    installed = package.parent / binary.name
    shutil.copy2(binary, installed)
    if digest(installed) != record["native"]["sha256"]:
        raise ValueError("OpenCV replacement copy differs")
    shutil.rmtree(package)
    for name, content in notices.items():
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    write_json(
        BUILD / "windows-opencv-replacement.json",
        {
            "originalWheelExtensionSha256": old_hash,
            "removedWheelPythonSha256": wrapper_hashes,
            "preservedWheelNoticesSha256": {
                str(name): digest(package / name) for name in notices
            },
            "sourceExtension": str(binary),
            "installedExtension": str(installed),
            "sha256": digest(installed),
            "buildVerificationSha256": digest(AUDIT / "build-verification.json"),
            "publicDistributionApproved": False,
        },
    )


def retain(resources: Path) -> None:
    record, _ = verified_build()
    notices = resources / "notices/source-built-opencv"
    for name, expected in record["noticeHashes"].items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or ":" in name
        ):
            raise ValueError("Unsafe source-built OpenCV notice path")
        path = AUDIT / "notices" / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Source-built OpenCV notice differs")
        target = notices / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    for name in ("build-verification.json", "CMakeCache.txt", "compile_commands.json"):
        path = AUDIT / name
        target = notices / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(
        BUILD / "windows-opencv-replacement.json", notices / "replacement.json"
    )
    source = record["inputs"]["source"]
    archive = AUDIT / "inputs" / source["filename"]
    if digest(archive) != source["sha256"]:
        raise ValueError("OpenCV preferred-source archive differs")
    destination = BUILD / "sources/source-built-opencv"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, destination / archive.name)
    for name in (
        "build-opencv-windows.py",
        "opencv-windows-probe.py",
        "windows_opencv_runtime.py",
    ):
        shutil.copy2(ROOT / "scripts" / name, destination / name)
    shutil.copy2(
        ROOT / "docs/windows-opencv-build-inputs.json", destination / "inputs.json"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("replace", "retain"))
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    args = parser.parse_args()
    replace() if args.command == "replace" else retain(args.resources)
