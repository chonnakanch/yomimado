"""Build the pinned Windows CPython source with pinned external inputs, outside macOS."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from windows_release import BUILD, ROOT, SERVICE, digest, fetch, read_json, write_json


def main() -> None:
    if sys.platform != "win32":
        raise ValueError("CPython PCbuild requires Windows")
    record = read_json(SERVICE / "windows-inputs.json")
    sources = BUILD / "sources"
    fetch(record["pythonSource"], sources / record["pythonSource"]["filename"])
    source = BUILD / ("Python-" + record["pythonVersion"])
    if source.exists():
        shutil.rmtree(source)
    with tarfile.open(sources / record["pythonSource"]["filename"]) as archive:
        for member in archive.getmembers():
            if (
                member.issym()
                or member.islnk()
                or not (BUILD / member.name).resolve().is_relative_to(BUILD.resolve())
            ):
                raise ValueError("Unsafe CPython source member")
        archive.extractall(BUILD)
    externals = source / "externals"
    for item in record["pythonExternals"]:
        path = sources / item["filename"]
        fetch(item, path)
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                relative = Path(*Path(name).parts[1:])
                target = externals / item["directory"] / relative
                if not target.resolve().is_relative_to(externals.resolve()):
                    raise ValueError("Unsafe external source member")
                if not name.endswith("/"):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
    # All required externals already exist, so get_externals skips downloads.
    env = os.environ.copy()
    env.update(IncludeTkinter="false", PYTHON=sys.executable)
    command = [
        "cmd.exe",
        "/c",
        str(source / "PCbuild/build.bat"),
        "-p",
        "x64",
        "-c",
        "Release",
        "--no-tkinter",
        "/p:PlatformToolset=v143",
        "/p:WindowsTargetPlatformVersion=10.0.26100.0",
    ]
    with (BUILD / "python-build.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    if result.returncode:
        print(
            (BUILD / "python-build.log").read_text(encoding="utf-8", errors="replace")[
                -12000:
            ]
        )
        raise RuntimeError("Windows CPython build failed")
    python = source / "PCbuild/amd64/python.exe"
    subprocess.run(
        [
            str(python),
            "-c",
            "import sys,ssl,lzma,sqlite3,ctypes; assert sys.version_info[:3] == (3,11,17); print(sys.version,ssl.OPENSSL_VERSION,sqlite3.sqlite_version)",
        ],
        check=True,
    )
    write_json(
        BUILD / "python-build.json",
        {
            "pythonVersion": record["pythonVersion"],
            "sources": [record["pythonSource"], *record["pythonExternals"]],
            "recipeSha256": digest(Path(__file__)),
            "command": command,
            "compiler": os.environ.get("VCToolsVersion"),
            "sdk": os.environ.get("WindowsSDKVersion"),
            "binaries": {
                p.name: digest(p)
                for p in python.parent.iterdir()
                if p.suffix.lower() in (".exe", ".dll", ".pyd")
            },
            "sourceCoverageApproved": False,
        },
    )
    notices = ROOT / "apps/desktop/src-tauri/resources/ocr/notices/python"
    for path in source.rglob("*"):
        if path.is_file() and path.name.lower().startswith(
            ("license", "licence", "copying", "notice", "copyright")
        ):
            target = notices / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    print(str(python))


if __name__ == "__main__":
    main()
