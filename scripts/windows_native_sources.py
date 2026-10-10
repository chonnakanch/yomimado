"""Retain Windows native preferred sources/notices without executing upstream code."""

from __future__ import annotations

import gzip
import hashlib
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from windows_notices import native_notice_source
from windows_onnx_sources import source_tree
from windows_release import BUILD, RESOURCES, ROOT, digest, read_json, write_json

MANIFEST = ROOT / "docs/windows-native-delivery-inputs.json"
PYTHON_MANIFEST = ROOT / "scripts/onnx-probe-inputs.json"


def retain_archive(
    entry: dict, original: Path, destination: Path, notices: Path
) -> dict:
    if (
        not entry["name"]
        or PurePosixPath(entry["name"]).name != entry["name"]
        or "\\" in entry["name"]
        or ":" in entry["name"]
    ):
        raise ValueError("Unsafe native source delivery name")
    if digest(original) != entry["sha256"]:
        raise ValueError("Original native source archive differs")
    destination.mkdir(parents=True, exist_ok=True)
    tree = destination / (entry["name"] + ".tar")
    excluded = source_tree(original, tree)
    if digest(tree) != entry["preferredSourceSha256"]:
        raise ValueError("Preferred native source tree differs")
    expected_notices = entry["noticeHashes"]
    if not expected_notices:
        raise ValueError("Native source has no pinned original notices")
    for name in expected_notices:
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or ":" in name
        ):
            raise ValueError("Unsafe native source notice path")
    copied = set()
    with tarfile.open(original, "r|*") as archive:
        for member in archive:
            name = member.name
            if name not in expected_notices:
                continue
            relative = PurePosixPath(name)
            if not member.isfile():
                raise ValueError("Native source notice is not a regular file")
            content = archive.extractfile(member).read()
            if hashlib.sha256(content).hexdigest() != expected_notices[name]:
                raise ValueError("Native source notice differs")
            target = notices / entry["name"] / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            copied.add(name)
    if copied != set(expected_notices):
        raise ValueError("Missing original native source notice")
    compressed = tree.with_suffix(".tar.gz")
    with (
        tree.open("rb") as source,
        compressed.open("wb") as output,
        gzip.GzipFile(
            filename="", fileobj=output, mode="wb", compresslevel=1, mtime=0
        ) as target,
    ):
        shutil.copyfileobj(source, target)
    tree.unlink()
    return {
        "name": entry["name"],
        "originalSha256": entry["sha256"],
        "preferredSourceSha256": entry["preferredSourceSha256"],
        "deliveryFilename": compressed.name,
        "deliverySha256": digest(compressed),
        "excluded": excluded,
    }


def collect(resources: Path = RESOURCES) -> None:
    destination = BUILD / "sources/windows-native"
    notices = resources / "notices/windows-native-sources"
    records = []
    packages = [
        package for package in read_json(PYTHON_MANIFEST) if package.get("source")
    ]
    python_records = []
    for package in packages:
        wheel = ROOT / "services/ocr/build/onnx-prototype/inputs" / package["filename"]
        original = BUILD / "native-source-inputs" / package["source"]["filename"]
        native_notice_source(package["source"], original)
        native_notice_source(package, wheel)
        python_records.append(verify_python_source(package, wheel, original))
    entries = read_json(MANIFEST)["archives"] + [
        package["source"] for package in packages
    ]
    if len({entry["name"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate source delivery identity")
    for entry in entries:
        original = BUILD / "native-source-inputs" / entry["filename"]
        print("Retaining native preferred source: " + entry["name"], flush=True)
        native_notice_source(entry, original)
        records.append(retain_archive(entry, original, destination, notices))
    record = {
        "manifestSha256": digest(MANIFEST),
        "pythonManifestSha256": digest(PYTHON_MANIFEST),
        "recipeSha256": digest(Path(__file__)),
        "sources": records,
        "pythonWheelSources": python_records,
        "sourceCoverageApproved": False,
        "publicDistributionApproved": False,
    }
    write_json(destination / "source-preparation.json", record)
    write_json(notices / "source-preparation.json", record)
    for target in (destination, notices):
        shutil.copy2(MANIFEST, target / MANIFEST.name)
        shutil.copy2(PYTHON_MANIFEST, target / PYTHON_MANIFEST.name)
    shutil.copy2(Path(__file__), destination / Path(__file__).name)
    for name in ("windows_notices.py", "windows_onnx_sources.py", "windows_release.py"):
        shutil.copy2(ROOT / "scripts" / name, destination / name)


def verify_python_source(package: dict, wheel: Path, original: Path) -> dict:
    """Bind all pure Python wheel code to unchanged preferred-source bytes."""
    if (
        digest(wheel) != package["sha256"]
        or digest(original) != package["source"]["sha256"]
    ):
        raise ValueError("Python wheel/source original differs")
    with zipfile.ZipFile(wheel) as archive:
        expected = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.endswith(".py") and ".dist-info/" not in name
        }
    if not expected:
        raise ValueError("Pure Python wheel contains no source files")
    prefix = package["source"]["wheelSourcePrefix"]
    found = {}
    with tarfile.open(original, "r|*") as archive:
        for member in archive:
            name = member.name.removeprefix(prefix)
            if member.name == name or name not in expected:
                continue
            if not member.isfile() or name in found:
                raise ValueError("Invalid Python preferred-source member")
            found[name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    if found != expected:
        raise ValueError("Python wheel code differs from preferred source")
    return {
        "package": package["package"],
        "wheelSha256": package["sha256"],
        "sourceSha256": package["source"]["sha256"],
        "pythonHashes": expected,
    }


if __name__ == "__main__":
    collect()
