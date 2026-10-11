"""Short, isolated source-only WebView2 loader probe; never changes the app."""

from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "services/ocr/build/webview-loader-probe"
REVISION = "cbbdee44afff22867de9fd88a9fc8350d9bdd399"
INPUTS = (
    (
        "webview-cbbdee44.tar.gz",
        "https://codeload.github.com/webview/webview/tar.gz/" + REVISION,
        "10e972a2327b5681474f4aa4499e505eaa4ff659aa995380386f08fd6fc1b763",
    ),
    (
        "microsoft.web.webview2.1.0.3650.58.nupkg",
        (
            "https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.3650.58/"
            "microsoft.web.webview2.1.0.3650.58.nupkg"
        ),
        "911a472128c82ac8baa0c486c23342cc9dd6e7dc50d754e676726642ca065c60",
    ),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    for filename, url, expected in INPUTS:
        path = BUILD / filename
        if not path.is_file() or sha(path) != expected:
            with urlopen(url, timeout=90) as response:
                path.write_bytes(response.read())
        if sha(path) != expected:
            raise ValueError("Original source/SDK checksum differs")
    source = BUILD / "source"
    source.mkdir(exist_ok=True)
    with tarfile.open(BUILD / INPUTS[0][0]) as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("Unsafe source path")
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("Unexpected source member")
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    tree = source / ("webview-" + REVISION)
    sdk = BUILD / "sdk"
    sdk.mkdir(exist_ok=True)
    with zipfile.ZipFile(BUILD / INPUTS[1][0]) as archive:
        # Only public headers/notices; no Microsoft loader object is extracted.
        for name in (
            "build/native/include/WebView2.h",
            "build/native/include/WebView2EnvironmentOptions.h",
            "LICENSE.txt",
            "NOTICE.txt",
        ):
            (sdk / Path(name).name).write_bytes(archive.read(name))
    fixes = {
        "core/include/webview/detail/platform/windows/webview2/loader.hh": (
            (
                "found_client.version.size() * sizeof(found_client.version[0])",
                "(found_client.version.size() + 1) * sizeof(found_client.version[0])",
            ),
            ('native_library m_lib{L"WebView2Loader.dll"};', "native_library m_lib{};"),
            ("return ERROR_SUCCESS;", "return E_NOINTERFACE;"),
        ),
        "core/include/webview/detail/platform/windows/version.hh": (
            (
                "info_buffer.reserve(info_buffer_length);",
                "info_buffer.resize(info_buffer_length);",
            ),
        ),
    }
    patches = []
    for name, replacements in fixes.items():
        path = tree / name
        original = path.read_text(encoding="utf-8")
        changed = original
        for before, after in replacements:
            if changed.count(before) != 1:
                raise ValueError("Source-only loader patch context differs")
            changed = changed.replace(before, after)
        path.write_text(changed, encoding="utf-8", newline="\n")
        patches.extend(
            difflib.unified_diff(
                original.splitlines(True),
                changed.splitlines(True),
                fromfile="a/" + name,
                tofile="b/" + name,
            )
        )
    (BUILD / "loader.patch").write_text("".join(patches), encoding="utf-8")
    return tree


def build_library(tree: Path) -> dict:
    common = [
        "cl",
        "/nologo",
        "/EHsc",
        "/std:c++14",
        "/MD",
        "/O2",
        "/DWEBVIEW_PLATFORM_WINDOWS",
        "/DWEBVIEW_EDGE",
        "/I" + str(tree / "core/include"),
        "/I" + str(BUILD / "sdk"),
    ]
    library = BUILD / "WebView2LoaderStatic.lib"
    obj = BUILD / "source-loader.obj"
    commands = [
        common
        + ["/c", str(ROOT / "scripts/source-webview-loader.cpp"), "/Fo:" + str(obj)],
        ["lib", "/nologo", "/MACHINE:X64", "/OUT:" + str(library), str(obj)],
    ]
    with (BUILD / "library-compile.log").open("w", encoding="utf-8") as log:
        for command in commands:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=90, check=False
            )
            log.write(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError("Source loader library compile failed")
    return {
        "commands": commands,
        "librarySha256": sha(library),
        "adapterSha256": sha(ROOT / "scripts/source-webview-loader.cpp"),
    }


def main() -> None:
    record = {
        "inputs": INPUTS,
        "sourceRevision": REVISION,
        "integratedIntoApp": False,
        "publicDistributionApproved": False,
    }
    try:
        tree = prepare()
        record.update(build_library(tree))
        record["patchSha256"] = sha(BUILD / "loader.patch")
        executable = BUILD / "loader-probe.exe"
        command = [
            "cl",
            "/nologo",
            "/EHsc",
            "/std:c++14",
            "/MD",
            "/O2",
            "/DWEBVIEW_PLATFORM_WINDOWS",
            "/DWEBVIEW_EDGE",
            "/I" + str(tree / "core/include"),
            "/I" + str(BUILD / "sdk"),
            str(ROOT / "scripts/probe-webview-loader.cpp"),
            "/Fe:" + str(executable),
            "/Fo:" + str(BUILD / "loader-probe.obj"),
            "/link",
            str(BUILD / "WebView2LoaderStatic.lib"),
            "advapi32.lib",
            "ole32.lib",
            "user32.lib",
            "version.lib",
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=90, check=False
        )
        (BUILD / "compile.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        record["command"] = command
        if result.returncode:
            raise RuntimeError("Loader probe compile failed; inspect compile.log")
        result = subprocess.run(
            [str(executable), str(BUILD / "profile")],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=BUILD,
            check=False,
        )
        (BUILD / "probe.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        record["probeOutput"] = result.stdout + result.stderr
        record["executableSha256"] = sha(executable)
        if result.returncode:
            raise RuntimeError("Loader environment/controller probe failed")
        record["passed"] = True
    except Exception as error:
        record["passed"] = False
        record["error"] = str(error)
        raise
    finally:
        BUILD.mkdir(parents=True, exist_ok=True)
        (BUILD / "verification.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
