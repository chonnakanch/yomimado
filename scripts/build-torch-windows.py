"""Build an isolated Eigen CPU Torch wheel; never modify or publish an installer."""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import venv
import zipfile
from pathlib import Path

from windows_release import ROOT, digest, fetch, read_json, write_json

BUILD = ROOT / "services/ocr/build/windows-torch-audit"
INPUTS = ROOT / "docs/windows-torch-build-inputs.json"
PROGRESS_INTERVAL = 30
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


def verify_commands(commands: list[dict]) -> dict:
    counts = {"cppCommands": 0, "resourceCommands": 0}
    for item in commands:
        suffix = Path(item["file"]).suffix.lower()
        if suffix == ".rc":
            # Windows resources do not include Eigen or link a C runtime.
            counts["resourceCommands"] += 1
            continue
        if suffix not in {".c", ".cc", ".cpp", ".cxx"}:
            raise ValueError("Unexpected Torch compiler input type")
        command = item["command"]
        if (
            "-DEIGEN_MPL2_ONLY" not in command
            or not all(
                re.search(r"(?:^|\s)[/-]D" + name + r"(?:=1)?(?:\s|$)", command)
                for name in ("WIN32", "_WINDOWS")
            )
            or not re.search(r"(?:^|\s)[/-]MD(?:\s|$)", command)
            or re.search(r"(?:^|\s)[/-]M(?:T[d]?|Dd)(?:\s|$)", command)
        ):
            raise ValueError(
                "Actual C/C++ command lacks MPL/platform guards or release DLL runtime"
            )
        counts["cppCommands"] += 1
    if not counts["cppCommands"]:
        raise ValueError("No Torch C/C++ compiler commands")
    return counts


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


def verify_required_files(directory: Path, repo: dict) -> dict:
    verified = {}
    for name, sha in repo.get("requiredFiles", {}).items():
        file = directory / name
        if not file.is_file() or digest(file) != sha:
            raise ValueError("Required source file missing or changed: " + name)
        verified[name] = sha
    return verified


def patch_nativert_header(text: str) -> str:
    blocks = (
        "#include <torch/csrc/distributed/c10d/Work.hpp>\n",
        (
            "  void setWork(int64_t workId, const c10::intrusive_ptr<c10d::Work>& work) {\n"
            "    work_[workId] = work;\n"
            "  }\n\n"
            "  c10::intrusive_ptr<c10d::Work> getWork(int64_t workId) const {\n"
            "    CHECK(work_.find(workId) != work_.end())\n"
            '        << "Couldn\'t find work with Id: " << workId;\n'
            "    return work_.at(workId);\n"
            "  }\n"
        ),
        "  std::unordered_map<int64_t, c10::intrusive_ptr<c10d::Work>> work_;\n",
    )
    for block in blocks:
        if text.count(block) != 1:
            raise ValueError("Original NativeRT Work declaration differs")
        text = text.replace(block, "#ifdef USE_DISTRIBUTED\n" + block + "#endif\n")
    return text


def apply_nativert_guard(source: Path, record: dict) -> dict:
    filename = record["filename"]
    header = source / filename
    if digest(header) != record["originalSha256"]:
        raise ValueError("Original NativeRT header checksum differs")
    original = header.read_bytes().decode("utf-8")
    patched = patch_nativert_header(original).encode("utf-8")
    if hashlib.sha256(patched).hexdigest() != record["patchedSha256"]:
        raise ValueError("Patched NativeRT header checksum differs")
    saved = BUILD / "originals" / filename
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(header, saved)
    patch = BUILD / "nativert-no-distributed.patch"
    patch.write_bytes(
        "".join(
            difflib.unified_diff(
                original.splitlines(True),
                patched.decode("utf-8").splitlines(True),
                fromfile="a/" + filename,
                tofile="b/" + filename,
            )
        ).encode("utf-8")
    )
    header.write_bytes(patched)
    report = {**record, "patchSha256": digest(patch)}
    write_json(BUILD / "nativert-source-patch.json", report)
    return report


def verify_no_distributed_work_symbols(text: str) -> None:
    if not text.strip():
        raise ValueError("NativeRT object symbol evidence missing")
    if any("UNDEF" in line and "Work@c10d@@" in line for line in text.splitlines()):
        raise ValueError("NativeRT object still references unavailable c10d::Work")


def log_tail(path: Path, limit: int = 12000) -> str:
    with path.open("rb") as log:
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - limit))
        return log.read().decode("utf-8", errors="replace")


def run(command: list[str], name: str, *, cwd=None, env=None) -> None:
    write_json(BUILD / (name + ".command.json"), command)
    print("Torch source audit: " + name, flush=True)
    path = BUILD / (name + ".log")
    started = time.monotonic()
    previous_size = 0
    with (
        path.open("w", encoding="utf-8") as log,
        subprocess.Popen(
            command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT
        ) as process,
    ):
        while True:
            try:
                returncode = process.wait(timeout=PROGRESS_INTERVAL)
                break
            except subprocess.TimeoutExpired:
                size = path.stat().st_size
                lines = log_tail(path, 2048).splitlines()
                last_line = lines[-1][:400] if lines else "No output yet"
                print(
                    f"Torch source audit: {name}: running "
                    f"{time.monotonic() - started:.0f}s; "
                    f"log {size} bytes (+{size - previous_size}); "
                    f"last output: {last_line}",
                    flush=True,
                )
                previous_size = size
    elapsed = time.monotonic() - started
    print(
        f"Torch source audit: {name}: exited {returncode} after {elapsed:.0f}s",
        flush=True,
    )
    if returncode:
        print(log_tail(path), flush=True)
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
                "-c",
                "core.eol=lf",
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
                raise ValueError(
                    "Preferred source notice differs: " + repo["path"] + "/" + name
                )
            target = notices / (repo["path"] or "pytorch") / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(directory / name, target)
        repositories.append(
            {
                "path": repo["path"],
                "revision": actual,
                "requiredFiles": verify_required_files(directory, repo),
            }
        )
    source_patch = apply_nativert_guard(source, record["nativertWorkGuard"])
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
    # Original headers, including pyconfig.h, are already staged and supplied
    # through Python_INCLUDE_DIR and INCLUDE. A quoted /I path here breaks the
    # upstream CXX_FLAGS entry in CAFFE2_BUILD_STRINGS (core/macros.h).
    flags = "-DEIGEN_MPL2_ONLY"
    env = os.environ.copy()
    env.update(
        {
            "PATH": str(BUILD / "venv/Scripts") + os.pathsep + env["PATH"],
            "PYTORCH_BUILD_VERSION": "2.8.0+cpu",
            "PYTORCH_BUILD_NUMBER": "1",
            "MAX_JOBS": "2",
            # Initialize with our extra guard while retaining CMake's Windows
            # defaults, including WIN32 used by upstream autograd fork guards.
            "CFLAGS": flags,
            "CXXFLAGS": flags,
            # Preserve the selected MSVC/SDK for upstream setuptools, and make
            # source-built CPython's original headers/import library available
            # to its small Python stub extension after native CMake installation.
            "DISTUTILS_USE_SDK": "1",
            "MSSdk": "1",
            "INCLUDE": str(python_include) + ";" + env.get("INCLUDE", ""),
            "LIB": str(base / "PCbuild/amd64") + ";" + env.get("LIB", ""),
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
    command_counts = verify_commands(commands)
    write_json(BUILD / "compiler-verification.json", command_counts)
    # Check the prior failing consumers before the long complete build, including
    # profiler headers still required when USE_KINETO is OFF.
    run(
        [
            cmake,
            "--build",
            str(build),
            "--target",
            "caffe2/CMakeFiles/torch_cpu.dir/core/common.cc.obj",
            "caffe2/CMakeFiles/torch_cpu.dir/__/torch/csrc/autograd/engine.cpp.obj",
            "caffe2/CMakeFiles/torch_cpu.dir/__/torch/csrc/autograd/profiler_kineto.cpp.obj",
            "caffe2/CMakeFiles/torch_cpu.dir/__/torch/nativert/executor/ExecutionFrame.cpp.obj",
            "caffe2/CMakeFiles/torch_cpu.dir/__/torch/nativert/kernels/C10Kernel.cpp.obj",
            "--parallel",
            "2",
        ],
        "compile-build-options",
        env=env,
    )
    symbol_checks = []
    for name, relative in (
        ("frame", "executor/ExecutionFrame.cpp.obj"),
        ("kernel", "kernels/C10Kernel.cpp.obj"),
    ):
        object_file = (
            build / "caffe2/CMakeFiles/torch_cpu.dir/__/torch/nativert" / relative
        )
        phase = "nativert-" + name + "-symbols"
        run(["dumpbin", "/symbols", str(object_file)], phase, env=env)
        log = BUILD / (phase + ".log")
        verify_no_distributed_work_symbols(log.read_text(errors="replace"))
        symbol_checks.append(
            {
                "object": str(object_file.relative_to(build)),
                "objectSha256": digest(object_file),
                "symbolLogSha256": digest(log),
                "unavailableWorkReferences": False,
            }
        )
    write_json(BUILD / "nativert-symbol-verification.json", symbol_checks)
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
    spec = importlib.util.spec_from_file_location(
        "torchvision_windows_build", ROOT / "scripts/build-torchvision-windows.py"
    )
    vision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vision)
    vision_report = vision.build(BUILD, python, env, run)
    write_json(
        BUILD / "build-verification.json",
        {
            "passed": True,
            "scope": "Independent source-built CPU Torch/torchvision wheels and probes",
            "auditRevision": os.environ["GITHUB_SHA"],
            "recipeSha256": digest(Path(__file__)),
            "wheelSha256": digest(wheel),
            "cmakeCacheSha256": digest(BUILD / "CMakeCache.txt"),
            "compilerCommands": command_counts,
            "sourcePatch": source_patch,
            "nativertSymbolChecks": symbol_checks,
            "nativeProbe": report,
            "torchvision": vision_report,
            "sourceCoverageApproved": False,
            "installedRuntimeVerified": False,
            "publicDistributionApproved": False,
        },
    )


if __name__ == "__main__":
    main()
