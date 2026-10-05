"""Fail the macOS release build if its Python environment has drifted."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import ssl
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
    if hashlib.sha256(recipe.read_bytes()).hexdigest() != record["recipeSha256"]:
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


def main() -> int:
    errors = []
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
