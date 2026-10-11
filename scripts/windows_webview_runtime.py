"""Bind the short source-only loader build to Windows Cargo and installed evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import probe_webview_loader as probe
import tomllib
from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    digest,
    pe_info,
    read_json,
    write_json,
)

RECORD = "windows-webview-loader.json"
ORIGINAL_LIBRARY = "0659b741bde6348d4c4a6ec4ceb9af50e3d0048ed9cd3c8659bccbb61fde55ee"
MARKER = b"YomiMado source WebView loader cbbdee44 ABI1"


def stage_desktop_crt() -> list[dict]:
    manifest = read_json(ROOT / "docs/windows-vc-runtime-inputs.json")
    vs = os.environ.get("VSINSTALLDIR")
    if not vs:
        raise ValueError("Canonical desktop CRT directory is unavailable")
    original = Path(vs) / "VC/Redist/MSVC" / manifest["redistDirectory"]
    destination = BUILD / "desktop-native"
    verified = []
    for name, expected in manifest["files"].items():
        source = original / name
        if digest(source) != expected or pe_info(source)["machine"] != "0x8664":
            raise ValueError("Canonical desktop CRT input differs")
        verified.append({"name": name, "sha256": expected, "source": str(source)})
    destination.mkdir(parents=True, exist_ok=True)
    if any(p.name not in manifest["files"] for p in destination.iterdir()):
        raise ValueError("Unexpected desktop native staging input")
    for entry in verified:
        shutil.copy2(entry["source"], destination / entry["name"])
    return verified


def check_original_crate(directory: Path, archive: Path, expected: str) -> None:
    if digest(archive) != expected:
        raise ValueError("WebView wrapper original archive differs from Cargo.lock")
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError("Unsafe wrapper source member")
            if member.isdir():
                continue
            if not member.isfile() or relative.parts[0] != directory.name:
                raise ValueError("Unexpected wrapper source member")
            expected_file = hashlib.sha256(
                source.extractfile(member).read()
            ).hexdigest()
            if digest(directory.joinpath(*relative.parts[1:])) != expected_file:
                raise ValueError("WebView wrapper cache differs from original archive")


def stage() -> None:
    if os.name != "nt":
        raise ValueError("Loader staging is restricted to native Windows builders")
    # The probe compiles and tests exactly the library subsequently used by Cargo.
    probe.main()
    verification = read_json(probe.BUILD / "verification.json")
    manifest = ROOT / "apps/desktop/src-tauri/Cargo.toml"
    data = json.loads(
        subprocess.check_output(
            [
                "cargo",
                "metadata",
                "--locked",
                "--format-version",
                "1",
                "--manifest-path",
                str(manifest),
            ],
            text=True,
            encoding="utf-8",
        )
    )
    selected = [
        p
        for p in data["packages"]
        if p["name"] == "webview2-com-sys" and p["version"] == "0.38.2"
    ]
    wry = [
        p for p in data["packages"] if p["name"] == "wry" and p["version"] == "0.55.1"
    ]
    if len(selected) != 1 or len(wry) != 1:
        raise ValueError("Unreviewed WebView wrapper/Wry version")
    directory = Path(selected[0]["manifest_path"]).parent
    archive = (
        directory.parents[2]
        / "cache"
        / directory.parent.name
        / (directory.name + ".crate")
    )
    lock = tomllib.loads(manifest.with_name("Cargo.lock").read_text(encoding="utf-8"))
    expected = next(
        p["checksum"]
        for p in lock["package"]
        if p["name"] == "webview2-com-sys" and p["version"] == "0.38.2"
    )
    check_original_crate(directory, archive, expected)
    original = directory / "x64/WebView2LoaderStatic.lib"
    if digest(original) != ORIGINAL_LIBRARY:
        raise ValueError("Original SDK static loader does not match the reviewed input")
    library = probe.BUILD / "WebView2LoaderStatic.lib"
    shutil.copy2(library, original)
    verification.update(
        {
            "originalSdkLibrarySha256": ORIGINAL_LIBRARY,
            "wrapperOriginalSha256": expected,
            "wrapperDirectory": str(directory),
            "stagedLibrary": str(original),
            "integratedIntoApp": True,
            "installedAppVerified": False,
        }
    )
    verification["desktopCrtInputs"] = stage_desktop_crt()
    write_json(BUILD / RECORD, verification)
    retain()


def retain() -> None:
    record = read_json(BUILD / RECORD)
    if (
        not record["passed"]
        or digest(Path(record["stagedLibrary"])) != record["librarySha256"]
    ):
        raise ValueError("Staged source loader library differs")
    sources = BUILD / "sources/webview-loader"
    notices = RESOURCES / "notices/source-webview-loader"
    sources.mkdir(parents=True, exist_ok=True)
    notices.mkdir(parents=True, exist_ok=True)
    retained = {}
    for filename, _, expected in probe.INPUTS:
        original = probe.BUILD / filename
        if digest(original) != expected:
            raise ValueError("Original source loader input differs")
        shutil.copy2(original, sources / filename)
        retained[filename] = expected
    for path in (
        probe.BUILD / "loader.patch",
        ROOT / "scripts/probe_webview_loader.py",
        ROOT / "scripts/probe-webview-loader.cpp",
        ROOT / "scripts/source-webview-loader.cpp",
        Path(__file__),
    ):
        shutil.copy2(path, sources / path.name)
        shutil.copy2(path, notices / path.name)
        retained[path.name] = digest(path)
    tree = probe.BUILD / "source" / ("webview-" + probe.REVISION)
    shutil.copy2(tree / "LICENSE", notices / "webview-LICENSE")
    for name in (
        "LICENSE.txt",
        "NOTICE.txt",
        "WebView2.h",
        "WebView2EnvironmentOptions.h",
    ):
        shutil.copy2(probe.BUILD / "sdk" / name, notices / name)
        shutil.copy2(probe.BUILD / "sdk" / name, sources / name)
        retained[name] = digest(probe.BUILD / "sdk" / name)
    record["retainedSources"] = retained
    write_json(BUILD / RECORD, record)
    write_json(notices / RECORD, record)


def verify(desktop: Path) -> dict:
    notices = desktop.parent / "ocr/notices/source-webview-loader"
    record = read_json(notices / RECORD)
    if (
        not record["passed"]
        or record["adapterSha256"] != digest(notices / "source-webview-loader.cpp")
        or record["adapterSha256"] != digest(ROOT / "scripts/source-webview-loader.cpp")
        or record["patchSha256"] != digest(notices / "loader.patch")
        or MARKER not in desktop.read_bytes()
    ):
        raise ValueError("Installed desktop is not bound to the source loader")
    manifest = read_json(ROOT / "docs/windows-vc-runtime-inputs.json")
    crt = {p["name"]: p["sha256"] for p in record["desktopCrtInputs"]}
    if crt != manifest["files"] or any(
        digest(desktop.parent / name) != expected for name, expected in crt.items()
    ):
        raise ValueError("Installed desktop CRT copies differ from canonical inputs")
    libraries = sorted(
        (ROOT / "apps/desktop/src-tauri/target").glob(
            "**/build/webview2-com-sys-*/out/x64/WebView2LoaderStatic.lib"
        )
    )
    if not libraries or any(digest(p) != record["librarySha256"] for p in libraries):
        raise ValueError("Cargo copied an unbound WebView loader library")
    record["cargoCopiedLibraries"] = [
        {"path": str(p), "sha256": digest(p)} for p in libraries
    ]
    record["installedDesktopSha256"] = digest(desktop)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage",))
    parser.parse_args()
    stage()
