"""Private Windows preparation and exact-input checks; never publishes a release."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from importlib import metadata
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/ocr"
BUILD = SERVICE / "build/windows"
RESOURCES = ROOT / "apps/desktop/src-tauri/resources/ocr"
FORBIDDEN = (".onnx", ".pt", ".pth", ".safetensors")
DETECTOR_SHA256 = "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f"

GENERATED_OUTPUTS = {
    "services/ocr/yomimado_ocr.egg-info/" + name
    for name in (
        "PKG-INFO",
        "SOURCES.txt",
        "dependency_links.txt",
        "requires.txt",
        "top_level.txt",
    )
} | {
    "apps/desktop/src-tauri/gen/schemas/" + name
    for name in (
        "acl-manifests.json",
        "capabilities.json",
        "desktop-schema.json",
        "macOS-schema.json",
        "windows-schema.json",
    )
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def restore_generated_outputs(revision: str) -> None:
    """Restore only known generated outputs in the initially clean build checkout."""
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, encoding="utf-8"
    ).strip()
    if head != revision:
        raise ValueError("Source revision changed during Windows build")
    changes = subprocess.check_output(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=ROOT,
        encoding="utf-8",
    ).split("\0")
    changes = [entry for entry in changes if entry]
    # Validate the entire change set before modifying any file. Never conceal
    # source, lock, staged, renamed or unrelated changes behind generation.
    unexpected = [
        entry
        for entry in changes
        if entry[:2] not in (" M", " D", "??") or entry[3:] not in GENERATED_OUTPUTS
    ]
    if unexpected:
        raise ValueError("Unexpected source changes during build: " + repr(unexpected))
    evidence = []
    for entry in changes:
        relative = entry[3:]
        path = ROOT / relative
        before = digest(path) if path.is_file() else None
        tracked = (
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        if tracked:
            subprocess.run(
                ["git", "restore", "--source", revision, "--worktree", "--", relative],
                cwd=ROOT,
                check=True,
            )
        else:
            path.unlink()
        evidence.append(
            {
                "path": relative,
                "generatedSha256": before,
                "restoredSha256": digest(path) if path.is_file() else None,
            }
        )
    write_json(BUILD / "windows-generated-outputs.json", evidence)
    print("Restored known generated build outputs: " + str(len(evidence)))


def fetch(record: dict, path: Path) -> None:
    """Never accept changed registry/dictionary/model bytes as a new pin."""
    if not path.exists() or digest(path) != record["sha256"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".download")
        try:
            with (
                urlopen(record["url"], timeout=120) as response,
                temporary.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
            if digest(temporary) != record["sha256"]:
                raise ValueError("Upstream checksum changed: " + path.name)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def validate_lock(record: dict) -> None:
    entries = record["packages"]
    expected = {
        line.strip()
        for line in (SERVICE / "requirements-windows-release.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.startswith("#")
    }
    actual = {e["name"] + "==" + e["version"] for e in entries}
    if expected != actual or len(entries) != len(actual):
        raise ValueError("Windows lock and input manifest differ")
    for item in entries:
        if (
            len(item["sha256"]) != 64
            or "/" in item["filename"]
            or "\\" in item["filename"]
        ):
            raise ValueError("Invalid input pin")
        if item["filename"].endswith(".whl"):
            _, python_tag, abi, target = (
                item["filename"].removesuffix(".whl").rsplit("-", 3)
            )
            compatible = (
                (python_tag == "cp311" and abi == "cp311" and target == "win_amd64")
                or (
                    python_tag in ("cp37", "cp38", "cp39", "cp310", "cp311")
                    and abi == "abi3"
                    and target == "win_amd64"
                )
                or (
                    python_tag in ("py3", "py2.py3")
                    and abi == "none"
                    and target in ("any", "win_amd64")
                )
            )
            if not compatible:
                raise ValueError(
                    "Wheel is not compatible with Windows CPython 3.11 x64: "
                    + item["filename"]
                )
    for name, version in (("torch", "2.8.0+cpu"), ("torchvision", "0.23.0+cpu")):
        entry = next(e for e in entries if e["name"] == name)
        if entry["version"] != version or not entry["url"].startswith(
            (
                "https://download.pytorch.org/whl/cpu/",
                "https://download-r2.pytorch.org/whl/cpu/",
            )
        ):
            raise ValueError("Only the pinned CPU Torch wheel is allowed")


def download_inputs() -> None:
    record = read_json(SERVICE / "windows-inputs.json")
    validate_lock(record)
    for entry in record["packages"]:
        print("Verifying pinned input: " + entry["filename"], flush=True)
        fetch(entry, BUILD / "inputs" / entry["filename"])
        if source := entry.get("source"):
            fetch(source, BUILD / "sources" / source["filename"])
    for entry in record.get("desktopVendorInputs", []):
        fetch(entry, BUILD / "sources/vendors" / entry["filename"])
    for entry in record.get("installerSourceInputs", []):
        fetch(entry, BUILD / "sources/installer" / entry["filename"])
    for entry in record.get("nativeNoticeInputs", []):
        from windows_notices import native_notice_source

        native_notice_source(
            entry, BUILD / "sources/native-notices" / entry["filename"]
        )
    # Collecting sdists does not approve embedded BLAS/codec/compiler libraries.
    write_json(BUILD / "download-record.json", record)


def derived_onnx_graphs(directory: Path) -> dict[Path, str]:
    """Allow only the four recorded conversions of the pinned learning models."""
    exported = directory / "assets/onnx"
    record_path = exported / "export.json"
    if not record_path.is_file():
        return {}
    record = read_json(record_path)
    expected_sources = {
        item["path"]: item["sha256"]
        for item in read_json(SERVICE / "windows-assets.json")
        if item["path"].startswith(("manga-ocr-base/", "opus-mt-ja-en/"))
    }
    expected_files = {
        "ocr-encoder.onnx",
        "ocr-decoder.onnx",
        "translation-encoder.onnx",
        "translation-decoder.onnx",
        "policies.json",
    }
    if (
        record.get("sourceInputs") != expected_sources
        or record.get("exporterSha256") != digest(ROOT / "scripts/export_onnx_probe.py")
        or set(record.get("outputs", {})) != expected_files
    ):
        raise ValueError("Unbound Windows inference conversion provenance")
    allowed = {}
    for name, sha in record["outputs"].items():
        path = exported / name
        if (
            not isinstance(sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", sha)
            or path.is_symlink()
            or sha == DETECTOR_SHA256
            or digest(path) != sha
        ):
            raise ValueError("Unapproved or changed Windows inference conversion")
        if name.endswith(".onnx"):
            allowed[path] = sha
    return allowed


def assert_no_detector(directory: Path) -> None:
    converted = derived_onnx_graphs(directory)
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected symlink: " + str(path))
        if path.is_file() and (
            (path.suffix.lower() in FORBIDDEN and path not in converted)
            or "comictextdetector.pt" in path.name.lower()
            or (path.stat().st_size > 10_000_000 and digest(path) == DETECTOR_SHA256)
        ):
            raise ValueError("Detector/unapproved weights in delivery: " + str(path))


def download_assets() -> None:
    assets = RESOURCES / "assets"
    for entry in read_json(SERVICE / "windows-assets.json"):
        target = assets / entry["path"]
        if not target.resolve().is_relative_to(assets.resolve()):
            raise ValueError("Unsafe asset path")
        fetch(entry, target)


def prepare_assets() -> None:
    download_assets()
    assets = RESOURCES / "assets"
    detector = BUILD / "detector"
    revision = "440b978563c71b758e31aaa315d100faba1efa2f"
    if not detector.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "https://github.com/dmMaze/comic-text-detector",
                str(detector),
            ],
            check=True,
        )
    subprocess.run(["git", "checkout", "--detach", revision], cwd=detector, check=True)
    if (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=detector, text=True, encoding="utf-8"
        ).strip()
        != revision
    ):
        raise ValueError("Detector source revision differs")
    destination = assets / "comic-text-detector"
    destination.mkdir(parents=True, exist_ok=True)
    # Copy tracked source only, with no examples, artwork, notebooks or weights.
    for relative in subprocess.check_output(
        ["git", "ls-files"], cwd=detector, text=True, encoding="utf-8"
    ).splitlines():
        path = Path(relative)
        if (
            path.suffix.lower() not in {".py", ".txt", ".yaml", ".yml"}
            and path.name != "LICENSE"
        ):
            continue
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(detector / path, target)
    subprocess.run(
        ["git", "apply", str(ROOT / "THIRD_PARTY_LICENSES/detector-inference.patch")],
        cwd=destination,
        check=True,
    )
    assert_no_detector(RESOURCES)


def pe_info(path: Path) -> dict:
    import pefile

    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(directories=[1, 13])
        imports = sorted(
            {
                item.dll.decode("ascii").lower()
                for group in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                for item in getattr(pe, group, [])
            }
        )
        return {
            "machine": hex(pe.FILE_HEADER.Machine),
            "subsystem": pe.OPTIONAL_HEADER.Subsystem,
            "imports": imports,
        }
    finally:
        pe.close()


def native_files(directory: Path):
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                is_pe = stream.read(2) == b"MZ"
            if is_pe:
                yield path
            elif path.suffix.lower() in (".exe", ".dll", ".pyd"):
                raise ValueError("Native filename is not a PE binary: " + str(path))


def analysis_native_inputs(toc: Path, fields: list[str]) -> list[dict]:
    """Read the pinned freezer's literal TOC; never execute its contents."""
    data = ast.literal_eval(toc.read_text(encoding="utf-8"))
    if not isinstance(data, tuple) or len(data) != len(fields):
        raise ValueError("Unexpected PyInstaller Analysis TOC schema")
    entries = data[fields.index("binaries")]
    if not isinstance(entries, list):
        raise TypeError("Missing PyInstaller binary analysis")
    inputs = []
    destinations = set()
    for entry in entries:
        if (
            not isinstance(entry, tuple)
            or len(entry) != 3
            or not all(isinstance(value, str) for value in entry)
            or entry[2] not in {"BINARY", "EXTENSION"}
        ):
            raise ValueError("Unexpected PyInstaller native input entry")
        destination, source, kind = entry
        # These are Windows destination paths even when tests run on macOS.
        relative = destination.replace("\\", "/")
        if (
            not relative
            or relative.startswith("/")
            or ":" in relative
            or any(p in {"", ".", ".."} for p in relative.split("/"))
            or relative.casefold() in destinations
        ):
            raise ValueError("Unsafe or duplicate PyInstaller native destination")
        destinations.add(relative.casefold())
        path = Path(source)
        if not path.is_absolute() or not path.is_file():
            raise ValueError("Missing absolute PyInstaller native source")
        inputs.append(
            {
                "component": "PyInstaller-discovered-native-input",
                "path": str(path),
                "destination": relative,
                "type": kind,
                "sha256": digest(path),
                **pe_info(path),
            }
        )
    if not inputs:
        raise ValueError("Empty PyInstaller native input analysis")
    return inputs


def executable_code_sha256(data: bytes) -> str:
    """Hash executable code independently of resource/checksum edits."""
    import hashlib

    import pefile

    with pefile.PE(data=data, fast_load=True) as executable:
        sections = [s for s in executable.sections if s.Name.rstrip(b"\0") == b".text"]
        if len(sections) != 1 or not sections[0].Misc_VirtualSize:
            raise ValueError("Missing unique bootloader code section")
        return hashlib.sha256(
            sections[0].get_data(length=sections[0].Misc_VirtualSize)
        ).hexdigest()


def frozen_executable_input(toc: Path, fields: list[str], frozen: Path) -> dict:
    """Bind the selected original bootloader and the exact appended application."""
    data = ast.literal_eval(toc.read_text(encoding="utf-8"))
    if not isinstance(data, tuple) or len(data) != len(fields):
        raise ValueError("Unexpected PyInstaller EXE TOC schema")
    values = dict(zip(fields, data, strict=True))
    entries = values["exefiles"]
    if (
        not isinstance(entries, list)
        or len(entries) != 1
        or not isinstance(entries[0], tuple)
        or len(entries[0]) != 3
        or entries[0][0] != "run.exe"
        or entries[0][2] != "EXECUTABLE"
        or values["append_pkg"] is not True
        or values["strip"] is not False
        or values["upx"] is not False
    ):
        raise ValueError("Unexpected Windows bootloader/build mode")
    bootloader = Path(entries[0][1])
    payload = Path(values["pkgname"])
    if not all(p.is_absolute() and p.is_file() for p in (bootloader, payload)):
        raise ValueError("Missing absolute freezer inputs")
    package = next(
        p
        for p in read_json(SERVICE / "windows-inputs.json")["packages"]
        if p["name"] == "pyinstaller"
    )
    wheel = BUILD / "inputs" / package["filename"]
    if digest(wheel) != package["sha256"]:
        raise ValueError("Original PyInstaller wheel differs")
    member = "PyInstaller/bootloader/Windows-64bit-intel/run.exe"
    with zipfile.ZipFile(wheel) as archive:
        original = archive.read(member)
    if (
        bootloader.read_bytes() != original
        or pe_info(bootloader)["machine"] != "0x8664"
    ):
        raise ValueError("Selected bootloader differs from original AMD64 wheel")
    executable = frozen.read_bytes()
    appended = payload.read_bytes()
    if (
        not appended
        or len(executable) <= len(appended)
        or not executable.endswith(appended)
    ):
        raise ValueError("Frozen executable does not contain the exact application PKG")
    code_hash = executable_code_sha256(original)
    if executable_code_sha256(executable) != code_hash:
        raise ValueError("Frozen executable changed original bootloader code")
    return {
        "bootloaderPath": str(bootloader),
        "bootloaderSha256": digest(bootloader),
        "bootloaderWheelMember": member,
        "wheelSha256": package["sha256"],
        "preferredSource": package["source"],
        "codeSectionSha256": code_hash,
        "applicationPkgSha256": digest(payload),
        "applicationPkgSize": len(appended),
        "applicationPkgOffset": len(executable) - len(appended),
        "frozenExecutableSha256": digest(frozen),
        "exeTocSha256": digest(toc),
        "sourceCoverageApproved": False,
    }


def inventory_inputs() -> None:
    """Inventory the actual interpreter, wheels and frozen image independently."""
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise ValueError("Input inventory requires native Windows x64 Python")
    inputs = []
    components = []
    notices = RESOURCES / "notices"
    licenses = notices / "licenses/python"
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        version = dist.version
        copied = []
        for item in dist.files or []:
            path = Path(dist.locate_file(item))
            if not path.is_file():
                continue
            if path.name.lower().startswith(
                ("license", "licence", "copying", "notice", "copyright")
            ):
                # Preserve relative paths: wheels can contain many vendor licences.
                target = licenses / f"{name}-{version}" / str(item).replace("..", "_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                copied.append(str(target.relative_to(notices)))
            if path.suffix.lower() in (".dll", ".pyd", ".exe"):
                inputs.append(
                    {
                        "component": name + "==" + version,
                        "path": str(path),
                        "sha256": digest(path),
                        **pe_info(path),
                    }
                )
        components.append(
            {
                "id": name + "==" + version,
                "licenseMetadata": dist.metadata.get("License-Expression")
                or dist.metadata.get("License"),
                "notices": copied,
                "review": "pending",
            }
        )
    base = Path(sys.base_prefix)
    for path in native_files(base):
        # Source-built Python has PCbuild outputs; official Python has DLLs.
        if "site-packages" not in path.parts:
            inputs.append(
                {
                    "component": "CPython-" + platform.python_version(),
                    "path": str(path),
                    "sha256": digest(path),
                    **pe_info(path),
                }
            )
    # Wheel/interpreter inventories do not cover DLLs discovered on the runner.
    # Bind the actual freezer source paths and hashes, including app-local VC
    # runtimes, without inferring redistribution permission from their location.
    import PyInstaller
    from PyInstaller.building.api import EXE
    from PyInstaller.building.build_main import Analysis

    if PyInstaller.__version__ != "6.16.0":
        raise ValueError("Requires pinned PyInstaller native input schema")
    toc = BUILD / "pyinstaller/yomimado-ocr/Analysis-00.toc"
    analyzed = analysis_native_inputs(toc, [g[0] for g in Analysis._GUTS])
    inputs.extend(analyzed)
    frozen = RESOURCES / "runtime"
    executable_input = frozen_executable_input(
        toc.with_name("EXE-00.toc"),
        [g[0] for g in EXE._GUTS],
        frozen / "yomimado-ocr.exe",
    )
    retained = notices / "windows-freeze"
    retained.mkdir(parents=True, exist_ok=True)
    for item in (
        toc,
        toc.with_name("EXE-00.toc"),
        toc.with_name("PKG-00.toc"),
        toc.with_name("PYZ-00.toc"),
        BUILD / "yomimado-ocr.spec",
    ):
        shutil.copy2(item, retained / item.name)
    executable_input["retainedBuildFiles"] = {
        item.name: digest(item) for item in retained.iterdir() if item.is_file()
    }
    by_hash = {}
    for item in inputs:
        by_hash.setdefault(item["sha256"], []).append(item)
    binaries = []
    for path in native_files(frozen):
        sha = digest(path)
        matches = by_hash.get(sha, [])
        binaries.append(
            {
                "path": str(path.relative_to(RESOURCES)).replace("\\", "/"),
                "sha256": sha,
                **pe_info(path),
                "buildInputs": matches,
                "review": "pending",
            }
        )
    record = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "inputManifestSha256": digest(SERVICE / "windows-inputs.json"),
        "components": components,
        "nativeInputs": inputs,
        "freezeAnalysis": {
            "pyinstallerVersion": PyInstaller.__version__,
            "analysisTocSha256": digest(toc),
            "recipeSha256": digest(ROOT / "scripts/build-windows-prerelease.ps1"),
            "nativeInputCount": len(analyzed),
            "executableInput": executable_input,
            "sourceCoverageApproved": False,
        },
        "binaries": binaries,
        "publicDistributionApproved": False,
    }
    write_json(notices / "windows-inventory.json", record)
    write_json(BUILD / "windows-inventory.json", record)


def native_configuration(*, backend: str = "torch") -> None:
    """Record compiled vendor versions/options for the exact Windows inputs."""
    import cv2
    import numpy
    import shapely
    from PIL import features

    if sys.platform != "win32":
        raise ValueError("Native configuration requires the Windows CPU environment")
    record = {
        "python": platform.python_version(),
        "backend": backend,
        "numpyBuild": numpy.show_config(mode="dicts"),
        "opencvBuild": cv2.getBuildInformation(),
        "geos": shapely.geos_version_string,
        "pillow": {name: features.version(name) for name in features.get_supported()},
        "inputManifestSha256": digest(SERVICE / "windows-inputs.json"),
        "publicDistributionApproved": False,
    }
    if backend == "torch":
        import torch

        if torch.version.cuda is not None:
            raise ValueError("CUDA Torch cannot enter this CPU candidate")
        record.update(
            torch=str(torch.__version__),
            torchCuda=None,
            torchBuild=torch.__config__.show(),
        )
    elif backend == "onnx":
        import onnxruntime

        if any(name.split(".")[0] in {"torch", "torchvision"} for name in sys.modules):
            raise ValueError("Torch leaked into ONNX configuration inspection")
        record.update(
            onnxruntime=onnxruntime.__version__,
            onnxruntimeBuild=onnxruntime.get_build_info(),
            availableProviders=onnxruntime.get_available_providers(),
            selectedProvider="CPUExecutionProvider",
            onnxInputManifestSha256=digest(ROOT / "scripts/onnx-probe-inputs.json"),
        )
    else:
        raise ValueError("Unknown Windows inference backend")
    write_json(BUILD / "windows-native-configuration.json", record)
    write_json(RESOURCES / "notices/windows-native-configuration.json", record)


def seal_resources(resources: Path) -> None:
    """Bind Python archives, data and notices as well as native binaries."""
    manifest = resources / "notices/windows-resource-hashes.json"
    files = {
        p.relative_to(resources).as_posix(): digest(p)
        for p in sorted(resources.rglob("*"))
        if p.is_file() and p != manifest
    }
    write_json(manifest, files)


def prune_unused_native() -> None:
    """Remove unused codecs and OS components supplied by Windows 11."""
    runtime = RESOURCES / "runtime"
    removed = []
    codecs = {
        "jpeg8.dll",
        "libjpeg.dll",
        "libpng16.dll",
        "libsharpyuv.dll",
        "libwebp.dll",
        "zlib.dll",
    }

    def remove(path, reason=None):
        removed.append(
            {
                "path": path.relative_to(RESOURCES).as_posix(),
                "sha256": digest(path),
                "reason": reason
                or "unused video/torchvision image-codec extension; PIL/OpenCV processing and torchvision ops retained",
            }
        )
        path.unlink()

    # Windows 11 supplies UCRT/API sets, WinTrust and DbgHelp. The Windows
    # system DbgHelp is explicitly not redistributable. Keep VC redistributables
    # app-local; they are not OS components. Validate the host's concrete OS
    # libraries before deleting anything, then prove loading in installed smoke.
    os_names = {"dbghelp.dll", "wintrust.dll", "ucrtbase.dll"}
    os_files = [
        path
        for path in native_files(runtime)
        if path.name.lower() in os_names
        or path.name.lower().startswith(("api-ms-win-", "ext-ms-win-"))
    ]
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    for path in os_files:
        if path.name.lower() in os_names:
            host = system / path.name.lower()
            if not host.is_file() or pe_info(host)["machine"] != "0x8664":
                raise ValueError("Missing native Windows OS dependency: " + path.name)
    for path in os_files:
        remove(path, "Windows 11 OS component; use the serviced system library/API set")

    for path in sorted(runtime.rglob("*")):
        if path.is_file() and (
            path.name.lower().startswith("opencv_videoio_ffmpeg")
            or (
                "torchvision" in path.relative_to(runtime).parts
                and path.name.lower() == "image.pyd"
            )
        ):
            remove(path)
    # PyInstaller may place dependent codec DLLs at the runtime root. Preserve
    # any codec still required by another native input, including dependencies
    # of retained codecs. Never strip a DLL solely because of its filename.
    native = [(path, pe_info(path)["imports"]) for path in native_files(runtime)]
    needed = {
        name
        for path, imports in native
        if path.name.lower() not in codecs
        for name in imports
    }
    while True:
        expanded = needed | {
            name
            for path, imports in native
            if path.name.lower() in needed
            for name in imports
        }
        if expanded == needed:
            break
        needed = expanded
    for path, _ in native:
        if path.name.lower() in codecs and path.name.lower() not in needed:
            remove(path)
    write_json(RESOURCES / "notices/windows-excluded-native.json", removed)


def verify_resources(
    resources: Path, *, manifest_hashes: dict[str, str] | None = None
) -> dict:
    assert_no_detector(resources)
    required = [
        "LICENSE",
        "MODEL_CREDITS.md",
        "ASSET_NOTICES.md",
        "windows-inventory.json",
        "project-revision.txt",
        "windows-inputs.json",
        "windows-assets.json",
        "distribution.json",
        "windows-resource-hashes.json",
    ]
    for name in required:
        if not (resources / "notices" / name).is_file():
            raise ValueError("Missing Windows notice/record: " + name)
    if not (resources / "runtime/yomimado-ocr.exe").is_file():
        raise ValueError("Missing Windows frozen executable")
    manifest = resources / "notices/windows-resource-hashes.json"
    actual_files = {
        p.relative_to(resources).as_posix(): digest(p)
        for p in sorted(resources.rglob("*"))
        if p.is_file() and p != manifest
    }
    if actual_files != read_json(manifest):
        raise ValueError("Installed resource hashes differ")
    manifest_names = {"windows-inputs.json", "windows-assets.json"}
    # New builds use current inputs. A historical exact-installer audit may
    # explicitly supply its independently pinned original manifest hashes.
    if manifest_hashes is None:
        manifest_hashes = {name: digest(SERVICE / name) for name in manifest_names}
    if set(manifest_hashes) != manifest_names or any(
        not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
        for sha in manifest_hashes.values()
    ):
        raise ValueError("Exact Windows manifest hashes required")
    for name, sha in manifest_hashes.items():
        if digest(resources / "notices" / name) != sha:
            raise ValueError("Installed input manifest differs: " + name)
    for entry in read_json(resources / "notices/windows-assets.json"):
        if digest(resources / "assets" / entry["path"]) != entry["sha256"]:
            raise ValueError("Installed asset changed: " + entry["path"])
    inventory = read_json(resources / "notices/windows-inventory.json")
    expected = {b["path"]: b["sha256"] for b in inventory["binaries"]}
    actual = {}
    for path in native_files(resources / "runtime"):
        info = pe_info(path)
        if info["machine"] != "0x8664":
            raise ValueError("Mixed/unsupported architecture: " + str(path))
        actual[str(path.relative_to(resources)).replace("\\", "/")] = digest(path)
    if not actual or actual != expected:
        raise ValueError("Installed native inventory differs")
    if any("cuda" in name.lower() or "cudnn" in name.lower() for name in actual):
        raise ValueError("CUDA binary in CPU candidate")
    if derived_onnx_graphs(resources):
        runtime_paths = [
            str(p.relative_to(resources / "runtime")).lower()
            for p in (resources / "runtime").rglob("*")
        ]
        if any(
            any(part in name for part in ("torch", "manga_ocr", "manga-ocr", "mkl"))
            for name in runtime_paths
        ):
            raise ValueError("Torch/MKL package or binary in ONNX runtime")
        if not any(Path(name).name == "onnxruntime.dll" for name in runtime_paths):
            raise ValueError("ONNX runtime native DLL is missing")
    bundled = {p.name.lower() for p in native_files(resources / "runtime")}
    if any(
        name in {"dbghelp.dll", "wintrust.dll", "ucrtbase.dll"}
        or name.startswith(("api-ms-win-", "ext-ms-win-"))
        for name in bundled
    ):
        raise ValueError("Windows OS component copied into runtime")
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    for entry in inventory["binaries"]:
        for name in entry["imports"]:
            if name in bundled or name.startswith(("api-ms-win-", "ext-ms-win-")):
                continue
            # VC runtimes must be app-local; a developer runner having them in
            # System32 is not evidence that a clean user's PC will have them.
            if (
                name != "msvcp_win.dll"
                and name.startswith(
                    (
                        "vcruntime",
                        "msvcp",
                        "vcomp",
                        "concrt",
                        "libiomp",
                        "mkl",
                        "cuda",
                        "cudnn",
                    )
                )
                or not (system / name).is_file()
            ):
                raise ValueError("Missing app-local native dependency: " + name)
    return inventory


def verify_desktop_gui(path: Path) -> None:
    info = pe_info(path)
    if info["machine"] != "0x8664":
        raise ValueError("Desktop executable is not x64")
    if info["subsystem"] != 2:  # IMAGE_SUBSYSTEM_WINDOWS_GUI
        raise ValueError("Desktop executable opens a console; expected Windows GUI")


def package(installer: Path, output: Path, installed: Path) -> None:
    verify_resources(installed / "ocr")
    verify_desktop_gui(installed / "yomimado.exe")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("Candidate must be built from a clean source tree")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if (installed / "ocr/notices/project-revision.txt").read_text().strip() != revision:
        raise ValueError("Installed source revision mismatch")
    from windows_notices import installer_inputs

    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "windows-installer-inputs.json", installer_inputs(installed, installer)
    )
    shutil.copy2(installer, output / installer.name)
    with tarfile.open(output / "windows-notices.tar.gz", "w:gz") as archive:
        archive.add(installed / "ocr/notices", arcname="notices")
    # Preserve original daily dictionary snapshots for reproducible rebuilds.
    with tarfile.open(
        output / "windows-dictionary-snapshots.tar.gz", "w:gz"
    ) as archive:
        for entry in read_json(SERVICE / "windows-assets.json"):
            if entry["path"] in ("JMdict_e.gz", "kanjidic2.xml.gz"):
                archive.add(
                    installed / "ocr/assets" / entry["path"], arcname=entry["path"]
                )
    # This is a private worksheet/source collection, not an approved GPL delivery.
    source = output / "windows-source-preparation.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(BUILD / "sources", arcname="sources")
        for path in (
            ROOT / "scripts/build-windows-prerelease.ps1",
            ROOT / "scripts/windows_release.py",
            SERVICE / "windows-inputs.json",
            ROOT / "scripts/windows_python.py",
            ROOT / "scripts/windows_notices.py",
            ROOT / "scripts/windows_dictionary_seed.py",
        ):
            archive.add(path, arcname="recipes/" + path.name)
        if (installed / "ocr/assets/onnx/export.json").is_file():
            for name in (
                "prepare_onnx_probe.py",
                "export_onnx_probe.py",
                "check_onnx_probe.py",
                "onnx_runtime_probe.py",
                "onnx_detector_probe.py",
                "onnx_generation.py",
                "onnx-probe-inputs.json",
            ):
                archive.add(ROOT / "scripts" / name, arcname="recipes/" + name)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            f"--output={output / 'project-sources.tar.gz'}",
            revision,
        ],
        cwd=ROOT,
        check=True,
    )
    assets = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    record = {
        "mode": "private-test",
        "platform": "windows-x64",
        "sourceRevision": revision,
        "installedAppVerified": False,
        "publicDistributionApproved": False,
        "assets": assets,
    }
    write_json(output / "windows-candidate.json", record)
    (output / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha}  {name}\n"
            for name, sha in {
                **assets,
                "windows-candidate.json": digest(output / "windows-candidate.json"),
            }.items()
        ),
        encoding="utf-8",
    )
    print(json.dumps(record))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "download",
            "download-assets",
            "assets",
            "inventory",
            "configuration",
            "prune",
            "seal",
            "verify",
            "package",
            "installer-inventory",
            "restore-generated",
        ],
    )
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    parser.add_argument("--installed", type=Path)
    parser.add_argument("--installer", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--backend", choices=("torch", "onnx"), default="torch")
    args = parser.parse_args()
    if args.command == "download":
        download_inputs()
    elif args.command == "download-assets":
        download_assets()
    elif args.command == "installer-inventory":
        if not args.installed or not args.installer:
            raise ValueError(
                "Installer inventory requires installed app and exact setup"
            )
        from windows_notices import installer_inputs

        installer_inputs(args.installed, args.installer)
    elif args.command == "restore-generated":
        if sys.platform != "win32" or not args.revision:
            raise ValueError(
                "Generated output restoration requires Windows and exact revision"
            )
        restore_generated_outputs(args.revision)
    elif args.command == "assets":
        prepare_assets()
    elif args.command == "inventory":
        inventory_inputs()
    elif args.command == "configuration":
        native_configuration(backend=args.backend)
    elif args.command == "prune":
        prune_unused_native()
    elif args.command == "seal":
        seal_resources(args.resources)
    elif args.command == "verify":
        verify_resources(args.resources)
    else:
        package(args.installer, args.output, args.installed)


if __name__ == "__main__":
    main()
