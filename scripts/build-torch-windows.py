"""Build an isolated Eigen CPU Torch wheel; never modify or publish an installer."""

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

BUILD = ROOT / "services/ocr/build/windows-torch-audit"
INPUTS = ROOT / "docs/windows-torch-build-inputs.json"
OFF = (
    "USE_OPENMP",
    "USE_MKLDNN",
    "USE_CUDA",
    "USE_ROCM",
    "USE_XPU",
    "USE_DISTRIBUTED",
    "USE_FBGEMM",
    "USE_KINETO",
    "USE_ITT",
    "USE_NNPACK",
    "USE_PYTORCH_QNNPACK",
    "USE_XNNPACK",
    "USE_MPS",
    "USE_VULKAN",
    "USE_FLASH_ATTENTION",
    "USE_MEM_EFF_ATTENTION",
    "USE_SYSTEM_LIBS",
    "USE_SYSTEM_EIGEN_INSTALL",
    "BUILD_TEST",
    "BUILD_CAFFE2",
    "BUILD_BINARY",
    "CAFFE2_USE_MSVC_STATIC_RUNTIME",
    "USE_MAGMA",
    "SLEEF_BUILD_DFT",
    "SLEEF_BUILD_QUAD",
    "SLEEF_BUILD_TESTS",
    "SLEEF_BUILD_BENCH",
    "SLEEF_ENABLE_CUDA",
)
ON = (
    "BUILD_PYTHON",
    "BUILD_SHARED_LIBS",
    "USE_NUMPY",
    "CMAKE_EXPORT_COMPILE_COMMANDS",
    "SLEEF_DISABLE_SSL",
    "SLEEF_DISABLE_FFTW",
    "SLEEF_DISABLE_MPFR",
    "CMAKE_DISABLE_FIND_PACKAGE_OpenSSL",
    "CMAKE_DISABLE_FIND_PACKAGE_OpenMP",
)


def verify_cache(cache: str) -> None:
    values = dict(re.findall(r"^([^#/:\n]+):[^=\n]+=(.*)$", cache, re.MULTILINE))
    for key, value in [(k, "OFF") for k in OFF] + [(k, "ON") for k in ON]:
        if values.get(key) != value:
            raise ValueError("Unexpected Torch CMake option: " + key)
    if values.get("BLAS") != "Eigen" or values.get("CMAKE_BUILD_TYPE") != "Release":
        raise ValueError("Unexpected Torch BLAS/build type")


def extract_eigen(archive: Path, record: dict, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not (member.isfile() or member.isdir()) or not (
                root / member.name
            ).resolve().is_relative_to(root):
                raise ValueError("Unsafe Eigen source member")
        for name, sha in record["licenseFiles"].items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest() != sha:
                raise ValueError("Eigen notice checksum differs")
        tar.extractall(root)


def run(command: list[str], name: str, *, cwd=None, env=None) -> None:
    write_json(BUILD / (name + ".command.json"), command)
    with (BUILD / (name + ".log")).open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    if result.returncode:
        print((BUILD / (name + ".log")).read_text(errors="replace")[-12000:])
        raise RuntimeError(name + " failed")


def main() -> None:
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
    BUILD.mkdir(parents=True, exist_ok=True)
    record = read_json(INPUTS)
    source = BUILD / "pytorch"
    if source.exists():
        shutil.rmtree(source)
    notices = BUILD / "notices"
    repositories = []
    for index, repo in enumerate(record["repositories"]):
        directory = source / repo["path"]
        directory.mkdir(parents=True, exist_ok=True)
        run(["git", "init", str(directory)], f"source-{index}-init")
        run(
            [
                "git",
                "-C",
                str(directory),
                "-c",
                "credential.helper=",
                "-c",
                "core.longpaths=true",
                "fetch",
                "--depth=1",
                repo["url"],
                repo["revision"],
            ],
            f"source-{index}-fetch",
        )
        run(
            [
                "git",
                "-C",
                str(directory),
                "-c",
                "core.longpaths=true",
                "checkout",
                "--detach",
                "FETCH_HEAD",
            ],
            f"source-{index}-checkout",
        )
        actual = subprocess.check_output(
            ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != repo["revision"]:
            raise ValueError("Preferred source commit differs")
        if repo["path"]:
            link = (
                subprocess.check_output(
                    ["git", "-C", str(source), "ls-tree", "HEAD", "--", repo["path"]],
                    text=True,
                )
                .strip()
                .split()
            )
            if link[:3] != ["160000", "commit", repo["revision"]]:
                raise ValueError("Torch parent gitlink differs from selected source")
        for name, sha in repo["noticeHashes"].items():
            if digest(directory / name) != sha:
                raise ValueError("Preferred source notice differs")
            target = notices / (repo["path"] or "pytorch") / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(directory / name, target)
        repositories.append({"path": repo["path"], "revision": actual})
    inputs = BUILD / "inputs"
    inputs.mkdir(exist_ok=True)
    eigen = record["eigen"]
    fetch(eigen, inputs / eigen["filename"])
    extract_eigen(inputs / eigen["filename"], eigen, BUILD / "eigen-source")
    shutil.copytree(
        BUILD / "eigen-source" / eigen["prefix"], source / "third_party/eigen"
    )
    for name in eigen["licenseFiles"]:
        relative = str(Path(name).relative_to(eigen["prefix"]))
        target = notices / "eigen" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / "third_party/eigen" / relative, target)
    write_json(
        BUILD / "source-verification.json",
        {
            "repositories": repositories,
            "eigen": eigen,
            "preferredSourcesVerified": True,
            "inputRecordSha256": digest(INPUTS),
            "sourceCoverageApproved": False,
        },
    )
    names = {
        "numpy",
        "typing-extensions",
        "sympy",
        "mpmath",
        "networkx",
        "jinja2",
        "markupsafe",
        "fsspec",
        "filelock",
        "pefile",
    }
    packages = [
        p
        for p in read_json(ROOT / "services/ocr/windows-inputs.json")["packages"]
        if p["name"].lower().replace("_", "-") in names
    ]
    if {p["name"].lower().replace("_", "-") for p in packages} != names:
        raise ValueError("Pinned Torch probe dependencies missing")
    tools = [
        *read_json(ROOT / "docs/windows-geos-build-inputs.json")["tools"],
        *record["tools"],
    ]
    for item in [*tools, *packages]:
        fetch(item, inputs / item["filename"])
        with zipfile.ZipFile(inputs / item["filename"]) as wheel:
            for name, sha in item.get("licenseFiles", {}).items():
                if hashlib.sha256(wheel.read(name)).hexdigest() != sha:
                    raise ValueError("Build-tool notice differs")
                target = notices / item["name"] / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(wheel.read(name))
    venv.create(BUILD / "venv", with_pip=True)
    python = str(BUILD / "venv/Scripts/python.exe")
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
    base = ROOT / "services/ocr/build/windows/Python-3.11.17"
    # CMake FindPython requires pyconfig.h alongside Python.h. Windows CPython
    # keeps it in PC; stage original bytes without changing the source build.
    python_include = BUILD / "python-include"
    if python_include.exists():
        shutil.rmtree(python_include)
    shutil.copytree(base / "Include", python_include)
    shutil.copy2(base / "PC/pyconfig.h", python_include / "pyconfig.h")
    write_json(
        BUILD / "python-header-staging.json",
        {
            "pythonBuildRecordSha256": digest(base.parent / "python-build.json"),
            "pyconfigSourceSha256": digest(base / "PC/pyconfig.h"),
            "stagedHeaders": {
                p.relative_to(python_include).as_posix(): digest(p)
                for p in sorted(python_include.rglob("*"))
                if p.is_file()
            },
        },
    )

    def path(value):
        return str(value).replace("\\", "/")

    cmake = str(BUILD / "venv/Scripts/cmake.exe")
    build = source / "build"
    flags = '-DEIGEN_MPL2_ONLY /I"' + path(base / "PC") + '"'
    env = os.environ.copy()
    env.update(
        {
            "PATH": str(BUILD / "venv/Scripts") + os.pathsep + env["PATH"],
            "PYTORCH_BUILD_VERSION": "2.8.0+cpu",
            "PYTORCH_BUILD_NUMBER": "1",
            "MAX_JOBS": "2",
        }
    )
    run(
        [
            cmake,
            "-S",
            str(source),
            "-B",
            str(build),
            "-G",
            "Ninja",
            *["-D" + key + "=OFF" for key in OFF],
            *["-D" + key + "=ON" for key in ON],
            "-DBLAS=Eigen",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL",
            "-DCMAKE_C_FLAGS=" + flags,
            "-DCMAKE_CXX_FLAGS=" + flags,
            "-DPython_EXECUTABLE=" + path(python),
            "-DPython_INCLUDE_DIR=" + path(python_include),
            "-DPython_LIBRARY=" + path(base / "PCbuild/amd64/python311.lib"),
            "-DCMAKE_INSTALL_PREFIX=" + path(source / "torch"),
        ],
        "configure",
        env=env,
    )
    shutil.copy2(build / "CMakeCache.txt", BUILD / "CMakeCache.txt")
    verify_cache((build / "CMakeCache.txt").read_text(errors="replace"))
    commands = read_json(build / "compile_commands.json")
    shutil.copy2(build / "compile_commands.json", BUILD / "compile_commands.json")
    if not commands or not all("-DEIGEN_MPL2_ONLY" in c["command"] for c in commands):
        raise ValueError("Actual commands lack MPL-only Eigen guard")
    run(
        [cmake, "--build", str(build), "--target", "install", "--parallel", "2"],
        "compile-install",
        env=env,
    )
    # Upstream egg_info disables a second native-dependency build. CMake already
    # installed it above; upstream bdist_wheel builds the Python stub and package.
    run([python, "setup.py", "egg_info", "bdist_wheel"], "wheel", cwd=source, env=env)
    (wheel,) = list((source / "dist").glob("torch-2.8.0+cpu-*.whl"))
    run(
        [python, "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        "install-torch",
        env=env,
    )
    run(
        [
            python,
            str(ROOT / "scripts/torch-windows-probe.py"),
            str(BUILD / "native-probe.json"),
        ],
        "native-probe",
        env=env,
    )
    report = read_json(BUILD / "native-probe.json")
    if report.get("passed") is not True:
        raise ValueError("CPU Torch probe did not pass")
    write_json(
        BUILD / "build-verification.json",
        {
            "passed": True,
            "scope": "Independent source-built CPU Torch wheel and tensor probe",
            "auditRevision": os.environ["GITHUB_SHA"],
            "recipeSha256": digest(Path(__file__)),
            "wheelSha256": digest(wheel),
            "cmakeCacheSha256": digest(BUILD / "CMakeCache.txt"),
            "nativeProbe": report,
            "sourceCoverageApproved": False,
            "installedRuntimeVerified": False,
            "publicDistributionApproved": False,
        },
    )


if __name__ == "__main__":
    main()
