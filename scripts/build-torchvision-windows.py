"""Build only matching CPU torchvision operators against the source-built Torch."""

from __future__ import annotations

import difflib
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path

from windows_release import ROOT, digest, fetch, read_json


def patch_setup(text: str) -> str:
    # OCR uses Pillow-backed transforms. Remove unused image/video extensions
    # from upstream's build list, retaining the CPU _C extension and Python APIs.
    for line in (
        "        make_image_extension(),\n",
        "        *make_video_decoders_extensions(),\n",
    ):
        if text.count(line) != 1:
            raise ValueError("Original torchvision extension list differs")
        text = text.replace(line, "")
    return text


def copy_pillow_notices(archive_path: Path, hashes: dict, destination: Path) -> None:
    if not hashes:
        raise ValueError("Pinned Pillow notice hashes missing")
    with zipfile.ZipFile(archive_path) as archive:
        for name, sha in hashes.items():
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != sha:
                raise ValueError("Pinned Pillow notice differs")
            target = destination / name
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Unsafe Pillow notice path")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def build(build: Path, python: str, env: dict, run) -> dict:
    record = read_json(ROOT / "docs/windows-torchvision-build-inputs.json")
    source = build / "torchvision"
    source.mkdir()
    run(["git", "init", str(source)], "vision-init")
    run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "credential.helper=",
            "fetch",
            "--depth=1",
            record["url"],
            record["revision"],
        ],
        "vision-fetch",
    )
    run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "core.eol=lf",
            "checkout",
            "--detach",
            "FETCH_HEAD",
        ],
        "vision-checkout",
    )
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if (
        revision != record["revision"]
        or digest(source / "setup.py") != record["setupSha256"]
    ):
        raise ValueError("Original torchvision source/setup identity differs")
    for name, sha in record["noticeHashes"].items():
        if digest(source / name) != sha:
            raise ValueError("Original torchvision notice differs")
        target = build / "notices/torchvision" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    original = (source / "setup.py").read_text(encoding="utf-8")
    patched = patch_setup(original)
    (source / "setup.py").write_text(patched, encoding="utf-8")
    patch = build / "torchvision-minimal.patch"
    patch.write_text(
        "".join(
            difflib.unified_diff(
                original.splitlines(True),
                patched.splitlines(True),
                fromfile="a/setup.py",
                tofile="b/setup.py",
            )
        ),
        encoding="utf-8",
    )
    pillow = next(
        p
        for p in read_json(ROOT / "services/ocr/windows-inputs.json")["packages"]
        if p["name"].lower() == "pillow"
    )
    if pillow["sha256"] != record["pillowWheelSha256"]:
        raise ValueError("Pillow notice record covers a different Windows wheel")
    fetch(pillow, build / "inputs" / pillow["filename"])
    copy_pillow_notices(
        build / "inputs" / pillow["filename"],
        record["pillowNoticeHashes"],
        build / "notices/pillow",
    )
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(build / "inputs" / pillow["filename"]),
        ],
        "vision-pillow",
        env=env,
    )
    vision_env = {
        **env,
        "BUILD_VERSION": "0.23.0+cpu",
        "FORCE_CUDA": "0",
        "TORCHVISION_USE_PNG": "0",
        "TORCHVISION_USE_JPEG": "0",
        "TORCHVISION_USE_WEBP": "0",
        "TORCHVISION_USE_NVJPEG": "0",
        "TORCHVISION_USE_VIDEO_CODEC": "0",
        "TORCHVISION_USE_FFMPEG": "0",
    }
    run([python, "setup.py", "bdist_wheel"], "vision-wheel", cwd=source, env=vision_env)
    (wheel,) = list((source / "dist").glob("torchvision-0.23.0+cpu-*.whl"))
    run(
        [python, "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        "vision-install",
        env=env,
    )
    run(
        [
            python,
            str(ROOT / "scripts/torchvision-windows-probe.py"),
            str(build / "torchvision-probe.json"),
        ],
        "vision-probe",
        env=env,
    )
    probe = read_json(build / "torchvision-probe.json")
    if probe.get("passed") is not True:
        raise ValueError("Matched torchvision CPU probe did not pass")
    return {
        "source": record,
        "patchSha256": digest(patch),
        "patchedSetupSha256": digest(source / "setup.py"),
        "wheelSha256": digest(wheel),
        "probe": probe,
        "publicDistributionApproved": False,
    }
