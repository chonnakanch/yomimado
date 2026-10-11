"""Retain Windows native preferred sources/notices without executing upstream code."""

from __future__ import annotations

import gzip
import hashlib
import shutil
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

from windows_notices import native_notice_source
from windows_onnx_sources import source_tree
from windows_release import BUILD, RESOURCES, ROOT, digest, read_json, write_json

MANIFEST = ROOT / "docs/windows-native-delivery-inputs.json"
PYTHON_MANIFEST = ROOT / "scripts/onnx-probe-inputs.json"


def verify_numpy_source(entry: dict, original: Path, wheel: Path, version: str) -> dict:
    """Bind the delivered NumPy version to its original preferred sources."""
    if digest(original) != entry["sha256"]:
        raise ValueError("NumPy preferred source original differs")
    with tarfile.open(original) as archive:
        member = archive.getmember(entry["name"] + "/PKG-INFO")
        if not member.isfile():
            raise ValueError("NumPy preferred source metadata is not regular")
        source_metadata = BytesParser().parsebytes(archive.extractfile(member).read())
    with zipfile.ZipFile(wheel) as archive:
        wheel_metadata = BytesParser().parsebytes(
            archive.read(f"numpy-{version}.dist-info/METADATA")
        )
    if any(
        record.get("Name", "").lower() != "numpy" or record.get("Version") != version
        for record in (source_metadata, wheel_metadata)
    ):
        raise ValueError("NumPy runtime and preferred-source versions differ")
    return {
        "version": version,
        "originalSha256": digest(original),
        "preferredSourceSha256": entry["preferredSourceSha256"],
    }


def verify_numpy_vendor(
    entry: dict, numpy_wheel: Path, supplier_wheel: Path, recipe: Path
) -> dict:
    """Bind the shipped BLAS bytes to the tagged supplier and unchanged recipe."""
    native_hashes = []
    notice_bytes = {}
    for key, path in (("numpyWheel", numpy_wheel), ("supplierWheel", supplier_wheel)):
        expected = entry[key]
        if digest(path) != expected["sha256"]:
            raise ValueError("NumPy vendor wheel differs")
        with zipfile.ZipFile(path) as archive:
            actual = hashlib.sha256(archive.read(expected["nativeMember"])).hexdigest()
            if actual != expected["nativeSha256"]:
                raise ValueError("NumPy vendor native member differs")
            native_hashes.append(actual)
            if key == "supplierWheel":
                for name, sha in entry["supplierNoticeHashes"].items():
                    relative = PurePosixPath(name)
                    if relative.is_absolute() or ".." in relative.parts or "\\" in name:
                        raise ValueError("Unsafe NumPy supplier notice path")
                    content = archive.read(name)
                    if hashlib.sha256(content).hexdigest() != sha:
                        raise ValueError("NumPy supplier notice differs")
                    notice_bytes[name] = content
    if native_hashes[0] != native_hashes[1] or not notice_bytes:
        raise ValueError("NumPy BLAS differs from its original supplier")
    with tarfile.open(recipe) as archive:
        for name, sha in entry["recipeFileHashes"].items():
            member = archive.getmember(entry["recipePrefix"] + name)
            if (
                not member.isfile()
                or hashlib.sha256(archive.extractfile(member).read()).hexdigest() != sha
            ):
                raise ValueError("NumPy supplier recipe differs")
    return {
        "nativeSha256": native_hashes[0],
        "numpyWheelSha256": entry["numpyWheel"]["sha256"],
        "supplierWheelSha256": entry["supplierWheel"]["sha256"],
        "supplierRevision": entry["supplierRevision"],
        "openblasRevision": entry["openblasRevision"],
        "recipeFileHashes": entry["recipeFileHashes"],
        "supplierNoticeHashes": entry["supplierNoticeHashes"],
        "noticeBytes": notice_bytes,
    }


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
    manifest = read_json(MANIFEST)
    entries = manifest["archives"] + [package["source"] for package in packages]
    if len({entry["name"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate source delivery identity")
    for entry in entries:
        original = BUILD / "native-source-inputs" / entry["filename"]
        print("Retaining native preferred source: " + entry["name"], flush=True)
        native_notice_source(entry, original)
        records.append(retain_archive(entry, original, destination, notices))
    vendor = manifest["numpyVendor"]
    supplier = vendor["supplierWheel"]
    supplier_wheel = BUILD / "native-source-inputs" / supplier["filename"]
    native_notice_source(supplier, supplier_wheel)
    recipe_entry = next(e for e in entries if e["name"] == vendor["recipeArchive"])
    numpy_record = verify_numpy_vendor(
        vendor,
        ROOT
        / "services/ocr/build/onnx-prototype/inputs"
        / vendor["numpyWheel"]["filename"],
        supplier_wheel,
        BUILD / "native-source-inputs" / recipe_entry["filename"],
    )
    source_entry = next(e for e in entries if e["name"] == vendor["sourceArchive"])
    numpy_record["preferredSource"] = verify_numpy_source(
        source_entry,
        BUILD / "native-source-inputs" / source_entry["filename"],
        ROOT
        / "services/ocr/build/onnx-prototype/inputs"
        / vendor["numpyWheel"]["filename"],
        vendor["numpyVersion"],
    )
    yaml_vendor = manifest["pyyamlVendor"]
    yaml_recipe = next(e for e in entries if e["name"] == yaml_vendor["recipeArchive"])
    with tarfile.open(
        BUILD / "native-source-inputs" / yaml_recipe["filename"]
    ) as archive:
        member = archive.getmember(yaml_vendor["recipeMember"])
        if (
            not member.isfile()
            or hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            != yaml_vendor["recipeSha256"]
        ):
            raise ValueError("PyYAML Windows recipe differs")
    for name, content in numpy_record.pop("noticeBytes").items():
        target = notices / "numpy-blas-supplier" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    record = {
        "manifestSha256": digest(MANIFEST),
        "pythonManifestSha256": digest(PYTHON_MANIFEST),
        "recipeSha256": digest(Path(__file__)),
        "sources": records,
        "pythonWheelSources": python_records,
        "numpyVendor": numpy_record,
        "pyyamlVendor": yaml_vendor,
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
