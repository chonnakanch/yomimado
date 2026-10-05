"""Build the source-pinned, image/ONNX-only OpenCV wheel for macOS releases.

Run with Python 3.11 on Apple Silicon. Build tools live in an ignored venv;
the OCR environment is changed only by explicitly installing the resulting wheel.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv
import zipfile
from pathlib import Path

from opencv_release import (
    NOTICES,
    OPTIONS,
    SOURCE_NAME,
    SOURCE_SHA256,
    SOURCE_URL,
    TOOLS,
    VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "services/ocr/build/opencv-source"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if (
        platform.system() != "Darwin"
        or platform.machine() != "arm64"
        or sys.version_info[:2] != (3, 11)
    ):
        parser.error("Requires Apple Silicon macOS with Python 3.11")
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    BUILD.mkdir(parents=True, exist_ok=True)
    archive = BUILD / SOURCE_NAME
    if not archive.exists():
        temporary = archive.with_suffix(".download")
        urllib.request.urlretrieve(SOURCE_URL, temporary)
        if digest(temporary) != SOURCE_SHA256:
            raise ValueError("OpenCV source download checksum mismatch")
        temporary.replace(archive)
    if digest(archive) != SOURCE_SHA256:
        raise ValueError("OpenCV source checksum mismatch")
    source = BUILD / "opencv-python-4.11.0.86"
    if source.exists():
        shutil.rmtree(source)
    with tarfile.open(archive) as tar:
        # The hashed upstream archive must not escape the build directory.
        for member in tar.getmembers():
            if (
                member.issym()
                or member.islnk()
                or not (BUILD / member.name).resolve().is_relative_to(BUILD)
            ):
                raise ValueError(f"Unsafe source archive member: {member.name}")
        tar.extractall(BUILD)
    build_venv = ROOT / "services/ocr/build/opencv-venv-py311"
    if not (build_venv / "bin/python").exists():
        venv.create(build_venv, with_pip=True)
    python = str(build_venv / "bin/python")
    subprocess.run([python, "-m", "pip", "install", *TOOLS], check=True)
    version_file = source / "cv2/version.py"
    version_file.write_text(
        "# Modified by YomiMado: identifies the image/ONNX-only build.\n"
        + version_file.read_text().replace('"4.11.0.86"', json.dumps(VERSION))
    )
    notice = (
        "YomiMado custom OpenCV build " + VERSION + "\n\n"
        "Built from the checksum-pinned opencv-python source distribution.\n"
        "FFmpeg and videoio are disabled and are not included.\n"
        "Highgui uses system Cocoa only for the detector's unused imshow import.\n"
        "Static dependencies below come from this same source archive.\n"
        "This software is based in part on the work of the Independent JPEG Group.\n"
    )
    for name in NOTICES:
        notice += "\n\n===== " + name + " =====\n\n" + (source / name).read_text()
    # Preserve module-level author notices too (including FLANN's BSD text).
    # Deduplicate full leading comment blocks, retaining their source paths.
    blocks = {}
    for module in (
        "core",
        "imgproc",
        "imgcodecs",
        "calib3d",
        "features2d",
        "flann",
        "dnn",
        "highgui",
        "python",
    ):
        for path in sorted((source / "opencv/modules" / module).rglob("*")):
            if not path.is_file() or path.suffix not in {".h", ".hpp", ".cpp", ".c"}:
                continue
            match = re.match(
                r"\s*(?:(?://[^\n]*(?:\n|$)|/\*.*?\*/)\s*)+",
                path.read_text(errors="replace"),
                re.DOTALL,
            )
            if match and re.search(
                r"copyright|license|redistribution", match[0], re.IGNORECASE
            ):
                blocks.setdefault(match[0].strip(), []).append(
                    str(path.relative_to(source))
                )
    for block, paths in blocks.items():
        notice += (
            "\n\n===== Module source notices: "
            + ", ".join(paths)
            + " =====\n\n"
            + block
            + "\n"
        )
    (source / "LICENSE-3RD-PARTY.txt").write_text(notice)
    changes = []
    with tarfile.open(archive) as tar:
        for name in ("cv2/version.py", "LICENSE-3RD-PARTY.txt"):
            original = (
                tar.extractfile("opencv-python-4.11.0.86/" + name).read().decode()
            )
            changes.extend(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    (source / name).read_text().splitlines(keepends=True),
                    fromfile="a/" + name,
                    tofile="b/" + name,
                )
            )
    (BUILD / "source-changes.diff").write_text("".join(changes))
    # Record exact modified files as well as the unmodified, matching source.
    modifications = BUILD / "modifications"
    modifications.mkdir(exist_ok=True)
    shutil.copy2(version_file, modifications / "version.py")
    shutil.copy2(
        source / "LICENSE-3RD-PARTY.txt", modifications / "LICENSE-3RD-PARTY.txt"
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": str(build_venv / "bin") + os.pathsep + env["PATH"],
            "CMAKE_ARGS": " ".join(OPTIONS),
            "CMAKE_BUILD_PARALLEL_LEVEL": str(args.jobs),
            "MACOSX_DEPLOYMENT_TARGET": "14.0",
            "CI_BUILD": "0",
            "ENABLE_CONTRIB": "0",
            "ENABLE_HEADLESS": "0",
            "ENABLE_ROLLING": "0",
            "ENABLE_JAVA": "0",
        }
    )
    with (BUILD / "build.log").open("w") as log:
        subprocess.run(
            [python, "setup.py", "bdist_wheel"],
            cwd=source,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    (wheel,) = (source / "dist").glob("*.whl")
    shutil.copy2(wheel, BUILD / wheel.name)
    shutil.copy2(
        next(source.glob("_skbuild/*/cmake-build/CMakeCache.txt")),
        BUILD / "CMakeCache.txt",
    )
    record = {
        "pythonVersion": sys.version.split()[0],
        "version": VERSION,
        "sourceUrl": SOURCE_URL,
        "sourceSha256": SOURCE_SHA256,
        "wheel": wheel.name,
        "wheelSha256": digest(wheel),
        "buildTools": TOOLS,
        "cmakeOptions": OPTIONS,
        "noticeSources": NOTICES,
        "modifiedFiles": {
            "cv2/version.py": digest(version_file),
            "LICENSE-3RD-PARTY.txt": digest(source / "LICENSE-3RD-PARTY.txt"),
        },
        "compiler": subprocess.check_output(["clang", "--version"], text=True).strip(),
        "sdk": subprocess.check_output(
            ["xcrun", "--show-sdk-version"], text=True
        ).strip(),
    }
    with zipfile.ZipFile(wheel) as zipped:
        (binary,) = [
            name
            for name in zipped.namelist()
            if name.startswith("cv2/") and name.endswith(".so")
        ]
        record["binarySha256"] = hashlib.sha256(zipped.read(binary)).hexdigest()
    subprocess.run(
        [python, "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheel)],
        check=True,
    )
    record["buildInformation"] = subprocess.check_output(
        [python, "-c", "import cv2; print(cv2.getBuildInformation())"], text=True
    )
    (BUILD / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    subprocess.run(
        [
            python,
            str(ROOT / "scripts/opencv_release.py"),
            str(BUILD / "build-record.json"),
        ],
        check=True,
    )
    delivery = BUILD / "source-delivery"
    delivery.mkdir(exist_ok=True)
    for path in (
        archive,
        BUILD / "source-changes.diff",
        BUILD / "build-record.json",
        ROOT / "scripts/build-opencv-macos.py",
        ROOT / "scripts/opencv_release.py",
    ):
        shutil.copy2(path, delivery / path.name)
    shutil.copytree(modifications, delivery / "modifications", dirs_exist_ok=True)
    (delivery / "BUILD.md").write_text(
        "# YomiMado image/ONNX-only OpenCV\n\n"
        "Use the matching YomiMado project source and Python 3.11 on an Apple Silicon Mac.\n"
        "Place the enclosed original source tarball in services/ocr/build/opencv-source/.\n"
        "Run python3 scripts/build-opencv-macos.py from the project root.\n"
        "The enclosed recipe copies match scripts/ in the project source.\n"
        "The recipe verifies the source SHA-256, creates a separate build venv, pins tools,\n"
        "applies the two documented version/notice changes, and builds with the recorded CMake flags.\n"
        "OpenCV code is unchanged; optional backends/modules are disabled by configuration.\n"
        "Source archive contains matching OpenCV, zlib, libpng, libjpeg-turbo and protobuf sources.\n"
        "The source diff and exact modified files are included. Compiler/SDK and binary/wheel hashes\n"
        "are in build-record.json. Binary hashes may change with toolchain/build location.\n"
        "Install the resulting wheel into the OCR venv with pip install --no-deps --force-reinstall.\n"
        "No publisher signing credentials are needed to rebuild this dependency.\n"
    )
    source_delivery = BUILD / "opencv-source-delivery.tar.gz"
    with tarfile.open(source_delivery, "w:gz") as tar:
        tar.add(delivery, arcname="opencv-source-delivery")
    print(f"Source delivery: {source_delivery} (SHA-256 {digest(source_delivery)})")
    print(f"Built {BUILD / wheel.name}; install explicitly with pip --no-deps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
