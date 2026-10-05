"""Fail the macOS release build if its Python environment has drifted."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import ssl
import subprocess
import sys
from pathlib import Path

LOCK = (
    Path(__file__).resolve().parents[1] / "services/ocr/requirements-macos-release.txt"
)
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")
SOURCES = {
    "Python-3.11.17.tgz": "53cdee63ac4bf12387b7b33a53d3b1f8f4941cad73807a7b4fe91bb001ef004a",
    "openssl-3.5.9.tar.gz": "603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a",
    "xz-5.8.4.tar.gz": "0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9",
}
NOTICES = {
    "CPython-LICENSE.txt",
    "Expat-COPYING.txt",
    "libmpdec-COPYRIGHT.txt",
    "OpenSSL-LICENSE.txt",
    "SHA3-LICENSE.txt",
    "Mersenne-Twister-NOTICE.txt",
    "BLAKE2-NOTICE.txt",
    "dtoa-NOTICE.txt",
    "SipHash-NOTICE.txt",
    "liblzma-LICENSE.txt",
    "XZ-COPYING.txt",
}


def runtime_recipe_digest(recipe: Path) -> str:
    text = recipe.read_text()
    if "if $prepare_runtime; then\n" not in text or "\nif $release; then" not in text:
        raise ValueError("Missing runtime recipe boundaries")
    block = text.split("if $prepare_runtime; then\n", 1)[1].split(
        "\nif $release; then", 1
    )[0]
    return hashlib.sha256(block.encode()).hexdigest()


def verify_runtime(base: Path, source: Path) -> None:
    record = json.loads((source / "build-record.json").read_text())
    if (
        record.get("pythonVersion") != "3.11.17"
        or record.get("opensslVersion") != "3.5.9"
        or record.get("lzmaVersion") != "5.8.4"
    ):
        raise ValueError("Release runtime version differs from source pins")
    if {item["filename"]: item["sha256"] for item in record["sources"]} != SOURCES:
        raise ValueError("Runtime source pins differ from the reviewed releases")
    recipe = LOCK.parents[2] / "scripts/build-macos-prerelease.sh"
    if (
        record.get("recipeScope") != "prepare-runtime"
        or runtime_recipe_digest(recipe) != record["recipeSha256"]
    ):
        raise ValueError("Runtime build recipe changed; prepare the runtime again")
    expected = {"bin/python3.11", "lib/libpython3.11.dylib"}
    expected.update(
        str(p.relative_to(base)) for p in base.glob("lib/python3.11/lib-dynload/*.so")
    )
    if set(record["binaries"]) != expected:
        raise ValueError("Runtime binary coverage differs from its build record")
    for name, digest in record["binaries"].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != digest:
            raise ValueError(
                f"Release interpreter binary differs from build record: {name}"
            )
    if set(record["noticeHashes"]) != NOTICES:
        raise ValueError("Runtime notice coverage is incomplete")
    for name, digest in record["noticeHashes"].items():
        path = (source / "notices" / name).resolve()
        if (
            not path.is_relative_to((source / "notices").resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Runtime notice differs from its build record")
    for name, digest in SOURCES.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Runtime source archive checksum mismatch")


NUMPY_SOURCE_SHA256 = "2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010"


def numpy_recipe_digest(recipe: Path) -> str:
    block = (
        recipe.read_text()
        .split("if $prepare_numpy; then\n", 1)[1]
        .split("\nif $prepare_runtime; then", 1)[0]
    )
    return hashlib.sha256(block.encode()).hexdigest()


def verify_numpy(site: Path, source: Path, configuration: dict) -> None:
    record = json.loads((source / "build-record.json").read_text())
    if (
        record.get("version") != "1.26.4"
        or record.get("sourceSha256") != NUMPY_SOURCE_SHA256
    ):
        raise ValueError("NumPy source version/checksum differs from reviewed input")
    if record.get("recipeSha256") != numpy_recipe_digest(
        LOCK.parents[2] / "scripts/build-macos-prerelease.sh"
    ):
        raise ValueError("NumPy build recipe changed; prepare NumPy again")
    if (
        configuration.get("Build Dependencies", {}).get("blas", {}).get("name")
        != "accelerate"
    ):
        raise ValueError("Release NumPy requires system Accelerate BLAS")
    if record.get("mesonArgs") != [
        "-Dblas=accelerate",
        "-Dlapack=accelerate",
        "-Duse-ilp64=true",
        "-Dallow-noblas=false",
    ]:
        raise ValueError("NumPy build options differ from the Accelerate recipe")
    paths = {p.relative_to(site).as_posix(): p for p in site.rglob("*.so")}
    if set(record["binaries"]) != set(paths) or not paths:
        raise ValueError("NumPy binary coverage differs from build record")
    for relative, path in paths.items():
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != record["binaries"][relative]
        ):
            raise ValueError("NumPy binary differs from its source build")
        links = subprocess.check_output(
            ["otool", "-L", str(path)], text=True
        ).splitlines()[1:]
        if any(
            not line.strip().startswith(("/usr/lib/", "/System/Library/"))
            for line in links
        ):
            raise ValueError("NumPy links a non-system native library")
    if list(site.rglob("*.dylib")):
        raise ValueError("NumPy contains bundled native runtime libraries")
    notice = site.parent / "numpy-1.26.4.dist-info/LICENSE.txt"
    if hashlib.sha256(notice.read_bytes()).hexdigest() != record["noticeSha256"]:
        raise ValueError("NumPy embedded notices differ from source build")
    if (
        hashlib.sha256((source / "numpy-1.26.4.tar.gz").read_bytes()).hexdigest()
        != NUMPY_SOURCE_SHA256
    ):
        raise ValueError("NumPy original source archive checksum mismatch")


def main() -> int:
    errors = []
    try:
        import numpy

        verify_numpy(
            Path(numpy.__file__).parent,
            LOCK.parent / "build/numpy-source",
            numpy.__config__.CONFIG,
        )
    except (ValueError, KeyError, OSError, IndexError) as error:
        errors.append(str(error))
    if sys.argv[1:] == ["--numpy-only"]:
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    if sys.version_info[:3] != (3, 11, 17):
        errors.append("The macOS release build requires source-built Python 3.11.17.")
    else:
        try:
            if not ssl.OPENSSL_VERSION.startswith("OpenSSL 3.5.9 "):
                raise ValueError("Release runtime requires pinned OpenSSL 3.5.9")
            verify_runtime(Path(sys.base_prefix), LOCK.parent / "build/python-source")
        except (ValueError, KeyError, OSError) as error:
            errors.append(str(error))
    for line in LOCK.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN.fullmatch(line)
        if not match:
            errors.append(f"Invalid release pin: {line}")
            continue
        name, expected = match.groups()
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"Missing {name}=={expected}")
            continue
        if actual != expected:
            errors.append(f"{name}: expected {expected}, installed {actual}")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Python release environment matches version pins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
