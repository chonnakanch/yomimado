"""Build GEOS sources and verify DLL replacement in a disposable PyInstaller probe.

No existing OCR resources, installer, candidate or macOS environment is changed.
Only textual diagnostics are exported by the accompanying Actions workflow.
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

from windows_release import ROOT, digest, fetch, pe_info, read_json, write_json

BUILD = ROOT / "services/ocr/build/windows-geos-audit"
INPUTS = ROOT / "docs/windows-geos-build-inputs.json"


def extract_source(archive: Path, destination: Path) -> Path:
    root = destination.resolve()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not (member.isfile() or member.isdir()) or not (
                root / member.name
            ).resolve().is_relative_to(root):
                raise ValueError("Unsafe GEOS source archive member: " + member.name)
        tar.extractall(root)
    return root / "geos-3.11.4"


def replacement_plan(runtime: Path, rebuilt: Path, inspect=pe_info) -> dict:
    """Use the C wrapper name actually imported by unchanged Shapely PYDs."""
    pyds = sorted((runtime / "shapely").glob("*.pyd"))
    if len(pyds) != 3:
        raise ValueError("Expected three pinned Shapely PYDs")
    wrappers = set()
    for path in pyds:
        info = inspect(path)
        if info["machine"] != "0x8664":
            raise ValueError("Non-AMD64 Shapely extension")
        wrappers.update(name for name in info["imports"] if name.startswith("geos_c"))
    if len(wrappers) != 1:
        raise ValueError("Expected one GEOS C wrapper import")
    wrapper = wrappers.pop()
    libs = runtime / "shapely.libs"
    original = sorted(libs.glob("geos*.dll"))
    if len(original) != 2 or not (libs / wrapper).is_file():
        raise ValueError("Unexpected original GEOS library layout")
    source_c, source_cpp = rebuilt / "geos_c.dll", rebuilt / "geos.dll"
    for path in (source_c, source_cpp, *original):
        if inspect(path)["machine"] != "0x8664":
            raise ValueError("Non-AMD64 GEOS library")
    if "geos.dll" not in inspect(source_c)["imports"]:
        raise ValueError("Rebuilt C wrapper must import rebuilt geos.dll")
    return {
        "remove": original,
        "copy": [(source_c, libs / wrapper), (source_cpp, libs / "geos.dll")],
        "pyds": pyds,
    }


def verify_probe(report: dict, expected: dict[str, str]) -> None:
    if (
        report.get("passed") is not True
        or report.get("frozen") is not True
        or report.get("machine", "").lower() != "amd64"
        or report.get("python") != "3.11.17"
        or report.get("shapely") != "2.0.7"
        or report.get("geos") != "3.11.4"
    ):
        raise ValueError("Frozen geometry probe did not pass with pinned versions")
    actual = {}
    for item in report.get("loadedGeos", []):
        path = str(Path(item["path"]).resolve()).lower()
        if path in actual:
            raise ValueError("Duplicate loaded GEOS library")
        actual[path] = item["sha256"]
    wanted = {
        str(Path(path).resolve()).lower(): value for path, value in expected.items()
    }
    if actual != wanted or len(wanted) != 2:
        raise ValueError("Probe loaded unexpected GEOS library paths/hashes")


def run(command: list[str], name: str, env=None) -> None:
    write_json(BUILD / (name + ".command.json"), command)
    with (BUILD / (name + ".log")).open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    if result.returncode:
        print((BUILD / (name + ".log")).read_text(errors="replace")[-10000:])
        raise RuntimeError(name + " failed")


def main() -> None:
    if (
        sys.platform != "win32"
        or platform.machine().lower() != "amd64"
        or sys.version_info[:3] != (3, 11, 17)
    ):
        raise ValueError("Requires source-built Windows x64 CPython 3.11.17")
    if os.environ.get("VCToolsVersion", "").rstrip("\\") != "14.44.35207":
        raise ValueError("Requires pinned MSVC 14.44.35207")
    if os.environ.get("WindowsSDKVersion", "").rstrip("\\") != "10.0.26100.0":
        raise ValueError("Requires pinned Windows SDK 10.0.26100.0")
    if not Path(INPUTS).is_file():
        raise ValueError("Missing GEOS source/tool pins")
    BUILD.mkdir(parents=True, exist_ok=True)
    record = read_json(INPUTS)
    lock = read_json(ROOT / "services/ocr/windows-inputs.json")
    package_names = {
        "numpy",
        "shapely",
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "altgraph",
        "pefile",
        "pywin32-ctypes",
        "setuptools",
        "packaging",
    }
    packages = [p for p in lock["packages"] if p["name"] in package_names]
    if {p["name"] for p in packages} != package_names:
        raise ValueError("Missing pinned geometry/freeze tools")
    write_json(
        BUILD / "probe-inputs.json",
        [
            {key: p[key] for key in ("name", "version", "filename", "url", "sha256")}
            for p in packages
        ],
    )
    inputs = BUILD / "inputs"
    inputs.mkdir(exist_ok=True)
    archive = inputs / record["source"]["filename"]
    fetch(record["source"], archive)
    with tarfile.open(archive) as original:
        for name, expected in record["source"]["licenseFiles"].items():
            if (
                hashlib.sha256(original.extractfile(name).read()).hexdigest()
                != expected
            ):
                raise ValueError("GEOS/vendor licence checksum mismatch")
    for item in [*record["tools"], *packages]:
        path = inputs / item["filename"]
        fetch(item, path)
        with zipfile.ZipFile(path) as wheel:
            for name, expected in item.get("licenseFiles", {}).items():
                if hashlib.sha256(wheel.read(name)).hexdigest() != expected:
                    raise ValueError("Build-tool licence checksum mismatch")
    work = BUILD / "source"
    work.mkdir(exist_ok=True)
    source = work / "geos-3.11.4"
    if source.exists():
        shutil.rmtree(source)
    extract_source(archive, work)
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
            *[str(inputs / p["filename"]) for p in [*record["tools"], *packages]],
        ],
        "install-tools",
    )
    cmake = str(python_dir / "Scripts/cmake.exe")
    ctest = str(python_dir / "Scripts/ctest.exe")
    ninja = str(python_dir / "Scripts/ninja.exe")
    build_dir, installed = BUILD / "cmake-build", BUILD / "geos-install"
    for path in (build_dir, installed):
        if path.exists():
            shutil.rmtree(path)
    options = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=ON",
        "-DBUILD_TESTING=ON",
        "-DBUILD_BENCHMARKS=OFF",
        "-DBUILD_WEBSITE=OFF",
        "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL",
        "-DCMAKE_INSTALL_PREFIX=" + str(installed),
        "-DCMAKE_MAKE_PROGRAM=" + ninja,
    ]
    env = os.environ.copy()
    env["PATH"] = str(python_dir / "Scripts") + os.pathsep + env["PATH"]
    run(
        [cmake, "-S", str(source), "-B", str(build_dir), "-G", "Ninja", *options],
        "configure",
        env,
    )
    cache = (build_dir / "CMakeCache.txt").read_text(errors="replace")
    for required in ("BUILD_SHARED_LIBS:BOOL=ON", "BUILD_TESTING:BOOL=ON"):
        if required not in cache:
            raise ValueError("GEOS CMake cache rejected " + required)
    run([cmake, "--build", str(build_dir), "--parallel", "4"], "compile", env)
    run(
        [ctest, "--test-dir", str(build_dir), "--output-on-failure", "--parallel", "4"],
        "ctest",
        env,
    )
    if "100% tests passed" not in (BUILD / "ctest.log").read_text(errors="replace"):
        raise ValueError("CTest did not execute the GEOS test suite")
    run([cmake, "--install", str(build_dir)], "install-geos", env)
    shutil.copy2(build_dir / "CMakeCache.txt", BUILD / "CMakeCache.txt")
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
            "geos-probe",
            "--distpath",
            str(BUILD / "dist"),
            "--workpath",
            str(BUILD / "freeze"),
            "--specpath",
            str(BUILD),
            str(ROOT / "scripts/geos-windows-probe.py"),
        ],
        "freeze-probe",
        env,
    )
    baseline = BUILD / "dist/geos-probe"
    # PE parsing is performed inside the pinned probe venv, which has pefile.
    run(
        [python, str(Path(__file__)), "--replace", str(baseline), str(installed)],
        "replace-test",
        env,
    )


def replace_test(baseline: Path, installed: Path) -> None:
    lock = read_json(ROOT / "services/ocr/windows-inputs.json")
    (shapely_input,) = [p for p in lock["packages"] if p["name"] == "shapely"]
    with zipfile.ZipFile(BUILD / "inputs" / shapely_input["filename"]) as wheel:
        for name in wheel.namelist():
            if name.endswith(".pyd") or (
                name.startswith("shapely.libs/geos") and name.endswith(".dll")
            ):
                path = baseline / "_internal" / name
                if digest(path) != hashlib.sha256(wheel.read(name)).hexdigest():
                    raise ValueError("Frozen probe changed pinned Shapely native bytes")
    replacement = BUILD / "replacement/geos-probe"
    if replacement.parent.exists():
        shutil.rmtree(replacement.parent)
    shutil.copytree(baseline, replacement)
    runtime = replacement / "_internal"
    plan = replacement_plan(runtime, installed / "bin")
    unchanged = [replacement / "geos-probe.exe", *plan["pyds"]]
    before = {str(p.relative_to(replacement)): digest(p) for p in unchanged}
    baseline_report = BUILD / "baseline.json"
    subprocess.run([str(baseline / "geos-probe.exe"), str(baseline_report)], check=True)
    baseline_data = read_json(baseline_report)
    original_libs = sorted((baseline / "_internal/shapely.libs").glob("geos*.dll"))
    verify_probe(baseline_data, {str(p): digest(p) for p in original_libs})
    removed = {str(p.relative_to(replacement)): digest(p) for p in plan["remove"]}
    for path in plan["remove"]:
        path.unlink()
    for src, dst in plan["copy"]:
        shutil.copy2(src, dst)
    if before != {str(p.relative_to(replacement)): digest(p) for p in unchanged}:
        raise ValueError("Replacement changed frozen EXE or Shapely extensions")
    replacement_report = BUILD / "replacement.json"
    subprocess.run(
        [str(replacement / "geos-probe.exe"), str(replacement_report)], check=True
    )
    replacement_data = read_json(replacement_report)
    verify_probe(replacement_data, {str(dst): digest(src) for src, dst in plan["copy"]})
    if baseline_data["fingerprint"] != replacement_data["fingerprint"]:
        raise ValueError("Replacement changed synthetic geometry results")
    record = {
        "passed": True,
        "scope": "Isolated frozen Shapely probe; full installed OCR replacement remains untested",
        "sourceCoverageApproved": False,
        "publicDistributionApproved": False,
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "inputs": read_json(INPUTS),
        "probeInputs": read_json(BUILD / "probe-inputs.json"),
        "commands": {p.name: read_json(p) for p in BUILD.glob("*.command.json")},
        "recipeSha256": digest(Path(__file__)),
        "probeSha256": digest(ROOT / "scripts/geos-windows-probe.py"),
        "python": sys.version,
        "compiler": os.environ.get("VCToolsVersion"),
        "sdk": os.environ.get("WindowsSDKVersion"),
        "runner": {
            "image": os.environ.get("ImageOS"),
            "version": os.environ.get("ImageVersion"),
        },
        "cmakeCacheSha256": digest(BUILD / "CMakeCache.txt"),
        "notices": {
            str(p.relative_to(BUILD / "source/geos-3.11.4")): digest(p)
            for p in (BUILD / "source/geos-3.11.4").rglob("*")
            if p.is_file()
            and p.name.lower().startswith(("copying", "license", "notice"))
        },
        "unchangedApplication": before,
        "removedLibraries": removed,
        "replacementLibraries": [
            {
                "source": str(src),
                "target": str(dst),
                "sha256": digest(src),
                **pe_info(src),
            }
            for src, dst in plan["copy"]
        ],
        "baseline": baseline_data,
        "replacement": replacement_data,
    }
    write_json(BUILD / "replacement-verification.json", record)
    print(
        "Pinned GEOS CTest and frozen DLL replacement pass; installer/source approval remains open."
    )


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--replace":
        replace_test(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
