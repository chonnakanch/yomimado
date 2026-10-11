"""Build only the pinned Windows Sudachi binding with a retained offline graph."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

import tomllib
from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    digest,
    fetch,
    pe_info,
    read_json,
    write_json,
)

MANIFEST = ROOT / "docs/windows-sudachi-build-inputs.json"
LOCK = ROOT / "docs/windows-sudachi-Cargo.lock"
AUDIT = BUILD / "sudachi"


def validate_inputs(inputs: dict, lock: Path) -> None:
    if digest(lock) != inputs["lockSha256"]:
        raise ValueError("Sudachi lock differs")
    entries = tomllib.loads(lock.read_text())["package"]
    expected = {
        (p["name"], p["version"]): p["checksum"]
        for p in entries
        if p.get("source", "").startswith("registry+")
    }
    actual = {(p["name"], p["version"]): p["sha256"] for p in inputs["crates"]}
    if actual != expected or len(actual) != len(inputs["crates"]):
        raise ValueError("Sudachi source inputs do not cover the exact lock")
    if not inputs["source"].get("noticeHashes") or any(
        not p.get("noticeHashes") for p in inputs["crates"]
    ):
        raise ValueError("Sudachi source is missing original notices")
    for update in inputs["manifestUpdates"]:
        name = PurePosixPath(update["path"])
        if name.is_absolute() or ".." in name.parts or "\\" in str(name):
            raise ValueError("Unsafe Sudachi manifest path")
        if (
            hashlib.sha256(update["content"].encode()).hexdigest()
            != update["updatedSha256"]
        ):
            raise ValueError("Sudachi manifest update differs")


def extract_original(
    entry: dict, archive: Path, directory: Path, notices: Path
) -> None:
    if digest(archive) != entry["sha256"]:
        raise ValueError("Sudachi original source differs")
    with tarfile.open(archive) as source:
        source.extractall(directory, filter="data")
        for name, sha in entry.get("noticeHashes", {}).items():
            member = source.getmember(name)
            if not member.isfile():
                raise ValueError("Sudachi notice is not a regular file")
            content = source.extractfile(member).read()
            if hashlib.sha256(content).hexdigest() != sha:
                raise ValueError("Sudachi original notice differs")
            target = notices / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def prepare(directory: Path = AUDIT) -> tuple[dict, Path, Path]:
    inputs = read_json(MANIFEST)
    validate_inputs(inputs, LOCK)
    if directory.exists():
        shutil.rmtree(directory)
    originals = directory / "originals"
    notices = directory / "notices"
    source = inputs["source"]
    original = originals / source["filename"]
    fetch(source, original)
    extract_original(source, original, directory / "source", notices)
    root = directory / "source" / source["prefix"]
    for update in inputs["manifestUpdates"]:
        path = root / update["path"]
        if digest(path) != update["originalSha256"]:
            raise ValueError("Sudachi original build manifest differs")
        path.write_bytes(update["content"].encode())
    shutil.copy2(LOCK, root / "Cargo.lock")
    vendor = directory / "vendor"
    for entry in inputs["crates"]:
        archive = originals / entry["filename"]
        fetch(entry, archive)
        extract_original(entry, archive, vendor, notices)
        crate = vendor / (entry["name"] + "-" + entry["version"])
        checksums = {
            path.relative_to(crate).as_posix(): digest(path)
            for path in sorted(crate.rglob("*"))
            if path.is_file() and path.name != ".cargo-checksum.json"
        }
        write_json(
            crate / ".cargo-checksum.json",
            {"files": checksums, "package": entry["sha256"]},
        )
    # Use a task-owned Cargo home. No global configuration or credentials enter it.
    cargo_home = directory / "cargo-home"
    cargo_home.mkdir()
    (cargo_home / "config.toml").write_text(
        '[source.crates-io]\nreplace-with = "retained"\n'
        "[source.retained]\ndirectory = " + json.dumps(str(vendor.resolve())) + "\n"
    )
    return inputs, root, cargo_home


def build() -> None:
    if sys.platform != "win32" or platform.machine().upper() != "AMD64":
        raise ValueError("Sudachi build requires Windows x64")
    inputs = read_json(MANIFEST)
    if platform.python_version() != inputs["pythonVersion"]:
        raise ValueError("Sudachi Python version differs")
    rust = subprocess.check_output(["rustc", "--version", "--verbose"], text=True)
    if f"release: {inputs['rustVersion']}\n" not in rust:
        raise ValueError("Sudachi Rust compiler differs")
    inputs, root, cargo_home = prepare()
    # PyO3 discovers the venv's conventional libs directory. Our interpreter
    # is built in-tree, so its actual import library lives under PCbuild.
    python_lib = (
        BUILD / ("Python-" + inputs["pythonVersion"]) / "PCbuild/amd64/python311.lib"
    )
    if not python_lib.is_file():
        raise ValueError("Source-built Python import library is missing")
    target = AUDIT / "target"
    env = {
        **os.environ,
        "CARGO_HOME": str(cargo_home.resolve()),
        "CARGO_TARGET_DIR": str(target.resolve()),
        "PYO3_PYTHON": sys.executable,
        "LIB": str(python_lib.parent.resolve()) + ";" + os.environ.get("LIB", ""),
    }
    command = [
        "cargo",
        "build",
        "--offline",
        "--locked",
        "--release",
        "--target",
        inputs["target"],
        "--package",
        "sudachipy",
        "--manifest-path",
        str(root / "python/Cargo.toml"),
        "--message-format=json-render-diagnostics",
    ]
    log = AUDIT / "compile.jsonl"
    with log.open("w") as stream:
        result = subprocess.run(
            command, env=env, stdout=stream, timeout=600, check=False
        )
    if result.returncode:
        raise ValueError("Sudachi binding build failed; see compile.jsonl")
    built = target / inputs["target"] / "release/sudachipy.dll"
    info = pe_info(built)
    if info["machine"] != "0x8664":
        raise ValueError("Sudachi binding is not x64")
    package = importlib.metadata.distribution("SudachiPy")
    extensions = list(Path(package.locate_file("sudachipy")).glob("sudachipy*.pyd"))
    if len(extensions) != 1 or package.version != "0.6.10":
        raise ValueError("Sudachi original wrapper differs")
    original_sha = digest(extensions[0])
    if original_sha != inputs["originalWheelExtensionSha256"]:
        raise ValueError("Sudachi wheel extension differs before replacement")
    shutil.copy2(built, extensions[0])
    compiled = sorted(
        {
            json.loads(line)["package_id"]
            for line in log.read_text().splitlines()
            if line.startswith("{")
            and json.loads(line).get("reason") == "compiler-artifact"
        }
    )
    write_json(
        AUDIT / "build-verification.json",
        {
            "passed": True,
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "inputManifestSha256": digest(MANIFEST),
            "lockSha256": digest(LOCK),
            "recipeSha256": digest(Path(__file__)),
            "rustc": rust,
            "msvc": os.environ.get("VCToolsVersion"),
            "sdk": os.environ.get("WindowsSDKVersion"),
            "pythonImportLibrary": {
                "path": str(python_lib.resolve()),
                "sha256": digest(python_lib),
            },
            "command": command,
            "compileLogSha256": digest(log),
            "compiledPackages": compiled,
            "originalWheelExtensionSha256": original_sha,
            "nativeSha256": digest(built),
            "installedExtension": str(extensions[0]),
            **info,
            "sourceCoverageApproved": False,
            "publicDistributionApproved": False,
        },
    )
    print(
        "Locked Windows Sudachi binding built; installed tokenization checks remain required.",
        flush=True,
    )


def retain() -> None:
    record = read_json(AUDIT / "build-verification.json")
    if (
        not record["passed"]
        or record["inputManifestSha256"] != digest(MANIFEST)
        or record["lockSha256"] != digest(LOCK)
        or record["compileLogSha256"] != digest(AUDIT / "compile.jsonl")
        or record["recipeSha256"] != digest(Path(__file__))
        or digest(Path(record["installedExtension"])) != record["nativeSha256"]
    ):
        raise ValueError("Sudachi replacement is unbound")
    destination = BUILD / "sources/source-built-sudachi"
    notices = RESOURCES / "notices/source-built-sudachi"
    shutil.copytree(AUDIT / "originals", destination / "originals", dirs_exist_ok=True)
    shutil.copytree(AUDIT / "notices", notices, dirs_exist_ok=True)
    for path in (
        MANIFEST,
        LOCK,
        Path(__file__),
        AUDIT / "build-verification.json",
        AUDIT / "compile.jsonl",
    ):
        for parent in (destination, notices):
            parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, parent / path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "retain"))
    args = parser.parse_args()
    build() if args.command == "build" else retain()
