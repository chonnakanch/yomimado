"""Prepare isolated Windows x64 prototype environments from exact prebuilt inputs.

No native compiler, freezer, installer, draft upload or release approval. The
3.11.9 hosted bootstrap is explicitly not the final 3.11.17 release runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

from windows_release import fetch, read_json, validate_lock, write_json

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "services/ocr/build/onnx-prototype"
EXCLUDED = {"torch", "torchvision", "manga-ocr", "torchsummary"}


def run(command, **kwargs):
    subprocess.run([str(item) for item in command], check=True, **kwargs)


def prepare() -> None:
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("Hosted prototype preparation requires Windows x64")
    lock = read_json(ROOT / "services/ocr/windows-inputs.json")
    validate_lock(lock)
    additions = read_json(ROOT / "scripts/onnx-probe-inputs.json")
    packages = lock["packages"]
    BUILD.mkdir(parents=True, exist_ok=True)
    for entry in packages + additions:
        print("Verifying prototype input " + entry["filename"], flush=True)
        fetch(entry, BUILD / "inputs" / entry["filename"])
    for name in ("baseline", "runtime"):
        venv = BUILD / name
        run([sys.executable, "-m", "venv", venv])
        python = venv / "Scripts/python.exe"
        tools = [e for e in packages if e["name"] in {"setuptools", "wheel"}]
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                *[BUILD / "inputs" / e["filename"] for e in tools],
            ]
        )
        selected = (
            list(packages)
            if name == "baseline"
            else [e for e in packages if e["name"] not in EXCLUDED]
        )
        extra_names = (
            {"onnx", "ml_dtypes"}
            if name == "baseline"
            else {
                "onnxruntime",
                "flatbuffers",
                "coloredlogs",
                "humanfriendly",
                "pyreadline3",
            }
        )
        selected += [e for e in additions if e["package"] in extra_names]
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                *[BUILD / "inputs" / e["filename"] for e in selected],
            ]
        )
        if name == "baseline":
            run(
                [
                    python,
                    ROOT / "scripts/create-manga-ocr-warmup.py",
                    venv / "Lib/site-packages/manga_ocr/assets/example.jpg",
                ]
            )
        else:
            installed = json.loads(
                subprocess.check_output(
                    [python, "-m", "pip", "list", "--format=json"], text=True
                )
            )
            if any(e["name"].lower().replace("_", "-") in EXCLUDED for e in installed):
                raise RuntimeError("Torch-related package present in the ONNX runtime")
    assets = BUILD / "assets"
    for entry in read_json(ROOT / "services/ocr/windows-assets.json"):
        if entry["path"].startswith(("manga-ocr-base/", "opus-mt-ja-en/")):
            fetch(entry, assets / entry["path"])
    source = BUILD / "detector-source"
    revision = "440b978563c71b758e31aaa315d100faba1efa2f"
    run(["git", "init", source])
    run(
        [
            "git",
            "-C",
            source,
            "fetch",
            "--depth=1",
            "https://github.com/dmMaze/comic-text-detector",
            revision,
        ]
    )
    run(["git", "-C", source, "checkout", "--detach", revision])
    destination = assets / "comic-text-detector"
    for relative in subprocess.check_output(
        ["git", "-C", source, "ls-files"], text=True
    ).splitlines():
        path = Path(relative)
        if (
            path.suffix.lower() not in {".py", ".txt", ".yaml", ".yml"}
            and path.name != "LICENSE"
        ):
            continue
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
    run(
        ["git", "apply", ROOT / "THIRD_PARTY_LICENSES/detector-inference.patch"],
        cwd=destination,
    )
    # Smoke-only user-installed input: kept apart from exports and artifact paths.
    fetch(
        {
            "url": "https://github.com/zyddnys/manga-image-translator/releases/download/beta-0.2.1/comictextdetector.pt.onnx",
            "sha256": "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f",
        },
        BUILD / "smoke-detector.onnx",
    )
    native = []
    for entry in additions:
        with zipfile.ZipFile(BUILD / "inputs" / entry["filename"]) as archive:
            for group in ("nativeInputs", "noticeInputs"):
                for name, expected in entry[group].items():
                    actual = hashlib.sha256(archive.read(name)).hexdigest()
                    if actual != expected:
                        raise ValueError("Wheel member hash differs: " + name)
                    if group == "nativeInputs":
                        data = archive.read(name)
                        if data[:2] != b"MZ":
                            raise ValueError("Expected a native PE member")
                        offset = struct.unpack_from("<I", data, 0x3C)[0]
                        if (
                            data[offset : offset + 4] != b"PE\x00\x00"
                            or struct.unpack_from("<H", data, offset + 4)[0] != 0x8664
                        ):
                            raise ValueError(
                                "Native prototype input is not AMD64: " + name
                            )
                        native.append(
                            {
                                "wheel": entry["filename"],
                                "path": name,
                                "sha256": actual,
                                "machine": "0x8664",
                            }
                        )
    write_json(
        BUILD / "preparation.json",
        {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "nativeWheelMembers": native,
            "sourceRevision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "publicDistributionApproved": False,
            "installedAppVerified": False,
        },
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
