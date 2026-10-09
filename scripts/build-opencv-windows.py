"""Audit a source-built Windows OpenCV PYD in an isolated frozen CPU probe.

Does not replace installer resources or approve public distribution. Build-only
inputs and binaries remain on the runner; Actions exports textual evidence only.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

from windows_release import ROOT, digest, fetch, read_json, write_json

BUILD = ROOT / "services/ocr/build/windows-opencv-audit"
INPUTS = ROOT / "docs/windows-opencv-build-inputs.json"
MODULES = {
    "core",
    "imgproc",
    "imgcodecs",
    "calib3d",
    "features2d",
    "flann",
    "dnn",
    "highgui",
    "python3",
}
OFF = (
    "WITH_IPP",
    "WITH_IPP_IW",
    "WITH_ITT",
    "WITH_FFMPEG",
    "WITH_GSTREAMER",
    "WITH_MSMF",
    "WITH_DSHOW",
    "WITH_CUDA",
    "WITH_CUBLAS",
    "WITH_CUDNN",
    "WITH_OPENCL",
    "WITH_OPENMP",
    "WITH_TBB",
    "WITH_LAPACK",
    "WITH_EIGEN",
    "WITH_ADE",
    "WITH_QT",
    "WITH_GTK",
    "WITH_WIN32UI",
    "WITH_OPENVX",
    "WITH_FLATBUFFERS",
    "OPENCV_DNN_TFLITE",
    "WITH_TIFF",
    "WITH_WEBP",
    "WITH_OPENJPEG",
    "WITH_JASPER",
    "WITH_OPENEXR",
    "WITH_AVIF",
    "WITH_GDAL",
    "WITH_GDCM",
    "WITH_QUIRC",
    "OPENCV_ENABLE_NONFREE",
    "BUILD_SHARED_LIBS",
    "BUILD_WITH_STATIC_CRT",
    "BUILD_TESTS",
    "BUILD_PERF_TESTS",
    "BUILD_EXAMPLES",
    "BUILD_DOCS",
    "BUILD_opencv_apps",
    "BUILD_opencv_java",
    "BUILD_opencv_python2",
    "BUILD_opencv_videoio",
    "BUILD_opencv_gapi",
)
ON = (
    "CMAKE_EXPORT_COMPILE_COMMANDS",
    "WITH_PROTOBUF",
    "BUILD_PROTOBUF",
    "WITH_PNG",
    "BUILD_PNG",
    "WITH_JPEG",
    "BUILD_JPEG",
    "BUILD_ZLIB",
    "BUILD_opencv_python3",
    "BUILD_opencv_highgui",
    "OPENCV_SKIP_PYTHON_LOADER",
)
FORBIDDEN = re.compile(
    r"^(?:lib)?(?:mkl|iomp|ipp|cudart|cublas|cudnn|nvrtc|opencv_videoio|avcodec|avformat)",
    re.IGNORECASE,
)


def cmake_path(path: Path | str) -> str:
    # OpenCV expands library paths through CMake source expressions. Native
    # backslashes such as D:\a become escapes there, even with subprocess argv.
    return str(path).replace("\\", "/")


def extract_source(archive: Path, destination: Path) -> Path:
    root = destination.resolve()
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            if not (item.isfile() or item.isdir()) or not (
                root / item.name
            ).resolve().is_relative_to(root):
                raise ValueError("Unsafe OpenCV source member: " + item.name)
        tar.extractall(root)
    return root / "opencv-python-4.11.0.86"


def verify_cache(cache: str) -> None:
    values = dict(re.findall(r"^([^#/:\n]+):[^=\n]+=(.*)$", cache, re.MULTILINE))
    for name, expected in [(key, "OFF") for key in OFF] + [(key, "ON") for key in ON]:
        if values.get(name) != expected:
            raise ValueError("Unexpected OpenCV CMake option: " + name)
    if (
        values.get("CMAKE_BUILD_TYPE") != "Release"
        or values.get("CMAKE_MSVC_RUNTIME_LIBRARY") != "MultiThreadedDLL"
    ):
        raise ValueError("Unexpected OpenCV build/runtime linkage")


def verify_information(info: str) -> None:
    modules = re.search(r"^\s*To be built:\s*(.+)$", info, re.MULTILINE)
    vendors = re.search(r"^\s*3rdparty dependencies:\s*(.+)$", info, re.MULTILINE)
    if not modules or set(modules[1].split()) != MODULES:
        raise ValueError("Unexpected OpenCV modules")
    if not vendors or set(vendors[1].split()) != {
        "libprotobuf",
        "libjpeg-turbo",
        "libpng",
        "zlib",
    }:
        raise ValueError("Unexpected OpenCV static vendors")
    if re.search(
        r"^\s*(?:Intel IPP|Intel IPP IW|FFMPEG|GStreamer|NVIDIA CUDA|OpenCL|OpenMP):\s*(?:YES|[0-9])",
        info,
        re.MULTILINE | re.IGNORECASE,
    ):
        raise ValueError("Forbidden OpenCV backend enabled")


def verify_compile_commands(commands: list[dict]) -> int:
    compiled = [
        item
        for item in commands
        if Path(item["file"]).suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}
    ]
    if not compiled:
        raise ValueError("Missing actual C/C++ compiler commands")
    for item in compiled:
        command = item["command"]
        # CMake/Ninja emits -MD for this MSVC toolchain; cl accepts both
        # prefixes. Reject static/debug forms regardless of their prefix.
        if not re.search(r"(?:^|\s)[/-]MD(?:\s|$)", command) or re.search(
            r"(?:^|\s)[/-](?:MTd?|MDd)(?:\s|$)", command
        ):
            raise ValueError(
                "OpenCV/vendor compiler command does not use Release DLL runtime: "
                + item["file"]
            )
    return len(compiled)


def verify_probe(report: dict, expected: Path, frozen: bool, binary_hash: str) -> None:
    if (
        report.get("passed") is not True
        or report.get("frozen") is not frozen
        or report.get("python") != "3.11.17"
        or report.get("machine", "").lower() != "amd64"
        or report.get("opencv") != "4.11.0"
    ):
        raise ValueError("Unexpected OpenCV probe platform/version/status")
    verify_information(report.get("buildInformation", ""))
    native = report.get("loadedOpenCV", [])
    if (
        len(native) != 1
        or str(Path(native[0]["path"]).resolve()).lower()
        != str(expected.resolve()).lower()
        or native[0]["sha256"] != binary_hash
    ):
        raise ValueError("Unexpected loaded OpenCV path/hash")
    for item in report.get("loadedModules", []):
        if FORBIDDEN.search(Path(item["path"]).name):
            raise ValueError("Forbidden loaded native dependency")
    if (
        report.get("detectorSha256") != read_json(INPUTS)["smokeDetector"]["sha256"]
        or len(report.get("detectorOutputs", [])) != 2
    ):
        raise ValueError("Missing pinned detector execution on both synthetic fixtures")


def run(command: list[str], name: str, env=None) -> None:
    write_json(BUILD / (name + ".command.json"), command)
    with (BUILD / (name + ".log")).open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    if result.returncode:
        print((BUILD / (name + ".log")).read_text(errors="replace")[-12000:])
        raise RuntimeError(name + " failed")


def main(detector: Path) -> None:
    if (
        sys.platform != "win32"
        or platform.machine().lower() != "amd64"
        or sys.version_info[:3] != (3, 11, 17)
    ):
        raise ValueError("Requires source-built Windows x64 CPython 3.11.17")
    if (
        os.environ.get("VCToolsVersion", "").rstrip("\\") != "14.44.35207"
        or os.environ.get("WindowsSDKVersion", "").rstrip("\\") != "10.0.26100.0"
    ):
        raise ValueError("Requires pinned MSVC/SDK")
    record = read_json(INPUTS)
    if digest(detector) != record["smokeDetector"]["sha256"]:
        raise ValueError("Smoke-only detector checksum differs")
    BUILD.mkdir(parents=True, exist_ok=True)
    inputs = BUILD / "inputs"
    inputs.mkdir(exist_ok=True)
    archive = inputs / record["source"]["filename"]
    fetch(record["source"], archive)
    with tarfile.open(archive) as tar:
        for name, value in record["source"]["licenseFiles"].items():
            if (
                hashlib.sha256(
                    tar.extractfile("opencv-python-4.11.0.86/" + name).read()
                ).hexdigest()
                != value
            ):
                raise ValueError("Source/vendor licence checksum differs")
    names = {
        "numpy",
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "altgraph",
        "pefile",
        "pywin32-ctypes",
        "setuptools",
        "packaging",
    }
    packages = [
        p
        for p in read_json(ROOT / "services/ocr/windows-inputs.json")["packages"]
        if p["name"] in names
    ]
    if {p["name"] for p in packages} != names:
        raise ValueError("Missing pinned probe inputs")
    tools = read_json(ROOT / "docs/windows-geos-build-inputs.json")["tools"]
    for item in [*tools, *packages]:
        path = inputs / item["filename"]
        fetch(item, path)
        with zipfile.ZipFile(path) as wheel:
            for name, value in item.get("licenseFiles", {}).items():
                if hashlib.sha256(wheel.read(name)).hexdigest() != value:
                    raise ValueError("Build-tool licence checksum differs")
    source_dir = BUILD / "source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source = extract_source(archive, source_dir)
    python_dir = BUILD / "venv"
    venv.create(python_dir, with_pip=True)
    python = str(python_dir / "Scripts/python.exe")
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            *[str(inputs / p["filename"]) for p in [*tools, *packages]],
        ],
        "install-tools",
    )
    cmake = str(python_dir / "Scripts/cmake.exe")
    numpy_include = subprocess.check_output(
        [python, "-c", "import numpy; print(numpy.get_include())"], text=True
    ).strip()
    site = Path(
        subprocess.check_output(
            [python, "-c", "import sysconfig; print(sysconfig.get_path('platlib'))"],
            text=True,
        ).strip()
    )
    base = ROOT / "services/ocr/build/windows/Python-3.11.17"
    build_dir = BUILD / "cmake-build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    options = [
        *["-D" + name + "=OFF" for name in OFF],
        *["-D" + name + "=ON" for name in ON],
        "-DBUILD_LIST=core,imgproc,imgcodecs,calib3d,dnn,highgui,python3",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL",
        '-DCMAKE_CXX_FLAGS=/I"' + cmake_path(base / "PC") + '"',
        "-DCMAKE_MAKE_PROGRAM=" + cmake_path(python_dir / "Scripts/ninja.exe"),
        "-DPYTHON3_EXECUTABLE=" + cmake_path(python),
        "-DPYTHON_DEFAULT_EXECUTABLE=" + cmake_path(python),
        "-DPYTHON3_INCLUDE_DIR=" + cmake_path(base / "Include"),
        "-DPYTHON3_INCLUDE_DIR2=" + cmake_path(base / "PC"),
        "-DPYTHON3_LIBRARY=" + cmake_path(base / "PCbuild/amd64/python311.lib"),
        "-DPYTHON3_NUMPY_INCLUDE_DIRS=" + cmake_path(numpy_include),
        "-DPYTHON3_PACKAGES_PATH=" + cmake_path(site),
        "-DOPENCV_PYTHON3_INSTALL_PATH=" + cmake_path(BUILD / "native"),
        "-DCMAKE_INSTALL_PREFIX=" + cmake_path(BUILD / "install"),
        "-DOPENCV_DOWNLOAD_PATH=" + cmake_path(BUILD / "downloads"),
    ]
    env = os.environ.copy()
    env["PATH"] = str(python_dir / "Scripts") + os.pathsep + env["PATH"]
    run(
        [
            cmake,
            "-S",
            str(source / "opencv"),
            "-B",
            str(build_dir),
            "-G",
            "Ninja",
            *options,
        ],
        "configure",
        env,
    )
    cache = build_dir / "CMakeCache.txt"
    shutil.copy2(cache, BUILD / "CMakeCache.txt")
    verify_cache(cache.read_text(errors="replace"))
    compiler_commands = build_dir / "compile_commands.json"
    shutil.copy2(compiler_commands, BUILD / "compile_commands.json")
    compiled_count = verify_compile_commands(read_json(compiler_commands))
    # Disabled optional vendors must not cause unrecorded network inputs.
    if list((BUILD / "downloads").rglob("*")):
        downloaded = [
            p
            for p in (BUILD / "downloads").rglob("*")
            if p.is_file() and p.name != ".gitignore"
        ]
        if downloaded:
            raise ValueError("Unexpected OpenCV vendor download")
    run(
        [
            cmake,
            "--build",
            str(build_dir),
            "--target",
            "opencv_python3",
            "--parallel",
            "4",
        ],
        "compile",
        env,
    )
    (binary,) = list(build_dir.rglob("cv2*.pyd"))
    binary_info = pe_info_in_venv(python, binary)
    if binary_info["machine"] != "0x8664":
        raise ValueError("OpenCV is not AMD64")
    if not any(name.startswith("vcruntime140") for name in binary_info["imports"]):
        raise ValueError(
            "OpenCV DLL runtime imports missing despite configured linkage"
        )
    shutil.copy2(binary, site / binary.name)
    run(
        [
            python,
            str(ROOT / "scripts/opencv-windows-probe.py"),
            str(BUILD / "native-probe.json"),
            str(detector),
            str(ROOT / "scripts/fixtures"),
        ],
        "native-probe",
        env,
    )
    native = read_json(BUILD / "native-probe.json")
    verify_probe(native, site / binary.name, False, digest(binary))
    run(
        [
            python,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--noupx",
            "--name",
            "opencv-probe",
            "--distpath",
            str(BUILD / "dist"),
            "--workpath",
            str(BUILD / "freeze"),
            "--specpath",
            str(BUILD),
            str(ROOT / "scripts/opencv-windows-probe.py"),
        ],
        "freeze-probe",
        env,
    )
    frozen = BUILD / "dist/opencv-probe"
    (frozen_binary,) = list((frozen / "_internal").rglob("cv2*.pyd"))
    if digest(frozen_binary) != digest(binary):
        raise ValueError("Freeze changed source-built OpenCV bytes")
    run(
        [
            str(frozen / "opencv-probe.exe"),
            str(BUILD / "frozen-probe.json"),
            str(detector),
            str(ROOT / "scripts/fixtures"),
        ],
        "frozen-probe",
        env,
    )
    frozen_report = read_json(BUILD / "frozen-probe.json")
    verify_probe(frozen_report, frozen_binary, True, digest(binary))
    if (
        native["geometry"] != frozen_report["geometry"]
        or native["detectorOutputs"] != frozen_report["detectorOutputs"]
    ):
        raise ValueError("Frozen probe changed image/geometry/detector results")
    notices = BUILD / "notices"
    notices.mkdir(exist_ok=True)
    for name in record["source"]["licenseFiles"]:
        target = notices / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    # Keep module-level attribution alongside the full static-vendor texts.
    blocks = {}
    for module in MODULES - {"python3"} | {"python"}:
        for path in sorted((source / "opencv/modules" / module).rglob("*")):
            if path.is_file() and path.suffix in {".h", ".hpp", ".c", ".cpp"}:
                match = re.match(
                    r"\s*(?:(?://[^\n]*(?:\n|$)|/\*.*?\*/)\s*)+",
                    path.read_text(errors="replace"),
                    re.DOTALL,
                )
                if match and re.search(
                    r"copyright|license|redistribution", match[0], re.IGNORECASE
                ):
                    blocks.setdefault(match[0].strip(), []).append(
                        str(path.relative_to(source))
                    )
    (notices / "module-notices.txt").write_text(
        "\n\n".join(
            "===== " + ", ".join(paths) + " =====\n" + block
            for block, paths in blocks.items()
        ),
        encoding="utf-8",
    )
    write_json(
        BUILD / "build-verification.json",
        {
            "passed": True,
            "scope": "Isolated source-built OpenCV native/frozen CPU detector probe; full installed OCR remains untested",
            "sourceCoverageApproved": False,
            "publicDistributionApproved": False,
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "inputs": record,
            "buildTools": tools,
            "probeInputs": [
                {k: p[k] for k in ("name", "version", "filename", "url", "sha256")}
                for p in packages
            ],
            "commands": {p.name: read_json(p) for p in BUILD.glob("*.command.json")},
            "recipeSha256": digest(Path(__file__)),
            "probeSha256": digest(ROOT / "scripts/opencv-windows-probe.py"),
            "cmakeCacheSha256": digest(BUILD / "CMakeCache.txt"),
            "compileCommandsSha256": digest(BUILD / "compile_commands.json"),
            "releaseDllRuntimeCompileCommands": compiled_count,
            "options": options,
            "compiler": os.environ["VCToolsVersion"],
            "sdk": os.environ["WindowsSDKVersion"],
            "runner": {
                "image": os.environ.get("ImageOS"),
                "version": os.environ.get("ImageVersion"),
            },
            "native": {"sha256": digest(binary), **pe_info_in_venv(python, binary)},
            "noticeHashes": {
                str(p.relative_to(notices)): digest(p)
                for p in notices.rglob("*")
                if p.is_file()
            },
            "nativeProbe": native,
            "frozenProbe": frozen_report,
        },
    )
    print(
        "Source OpenCV CPU detector/native/frozen checks pass; installer and source approval remain open."
    )


def pe_info_in_venv(python: str, binary: Path) -> dict:
    # The source interpreter intentionally has no unpinned build dependencies.
    command = [
        python,
        "-c",
        "import json,sys; sys.path.insert(0,sys.argv[1]); from pathlib import Path; from windows_release import pe_info; print(json.dumps(pe_info(Path(sys.argv[2]))))",
        str(ROOT / "scripts"),
        str(binary),
    ]
    import json

    info = json.loads(subprocess.check_output(command, text=True))
    if any(FORBIDDEN.search(name) for name in info["imports"]):
        raise ValueError("Forbidden OpenCV native import")
    return info


if __name__ == "__main__":
    main(Path(sys.argv[1]))
