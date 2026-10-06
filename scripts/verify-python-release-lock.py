"""Fail the macOS release build if its Python environment has drifted."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
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


def runtime_recipe_digest(recipe: Path) -> str:
    text = recipe.read_text()
    if "if $prepare_runtime; then\n" not in text or "\nif $release; then" not in text:
        raise ValueError("Missing runtime recipe boundaries")
    block = text.split("if $prepare_runtime; then\n", 1)[1].split(
        "\nif $release; then", 1
    )[0]
    return hashlib.sha256(block.encode()).hexdigest()


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
    if (
        record.get("recipeScope") != "prepare-runtime"
        or runtime_recipe_digest(recipe) != record["recipeSha256"]
    ):
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


NUMPY_SOURCE_SHA256 = "2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010"


def numpy_recipe_digest(recipe: Path) -> str:
    block = (
        recipe.read_text()
        .split("if $prepare_numpy; then\n", 1)[1]
        .split("\nif $prepare_runtime; then", 1)[0]
    )
    return hashlib.sha256(block.encode()).hexdigest()


def verify_numpy(site: Path, source: Path, configuration: dict) -> None:
    record = json.loads((source / "build-record.json").read_text())
    if (
        record.get("version") != "1.26.4"
        or record.get("sourceSha256") != NUMPY_SOURCE_SHA256
    ):
        raise ValueError("NumPy source version/checksum differs from reviewed input")
    if record.get("recipeSha256") != numpy_recipe_digest(
        LOCK.parents[2] / "scripts/build-macos-prerelease.sh"
    ):
        raise ValueError("NumPy build recipe changed; prepare NumPy again")
    if (
        configuration.get("Build Dependencies", {}).get("blas", {}).get("name")
        != "accelerate"
    ):
        raise ValueError("Release NumPy requires system Accelerate BLAS")
    if record.get("mesonArgs") != [
        "-Dblas=accelerate",
        "-Dlapack=accelerate",
        "-Duse-ilp64=true",
        "-Dallow-noblas=false",
    ]:
        raise ValueError("NumPy build options differ from the Accelerate recipe")
    paths = {p.relative_to(site).as_posix(): p for p in site.rglob("*.so")}
    if set(record["binaries"]) != set(paths) or not paths:
        raise ValueError("NumPy binary coverage differs from build record")
    for relative, path in paths.items():
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != record["binaries"][relative]
        ):
            raise ValueError("NumPy binary differs from its source build")
        links = subprocess.check_output(
            ["otool", "-L", str(path)], text=True
        ).splitlines()[1:]
        if any(
            not line.strip().startswith(("/usr/lib/", "/System/Library/"))
            for line in links
        ):
            raise ValueError("NumPy links a non-system native library")
    if list(site.rglob("*.dylib")):
        raise ValueError("NumPy contains bundled native runtime libraries")
    notice = site.parent / "numpy-1.26.4.dist-info/LICENSE.txt"
    if hashlib.sha256(notice.read_bytes()).hexdigest() != record["noticeSha256"]:
        raise ValueError("NumPy embedded notices differ from source build")
    if (
        hashlib.sha256((source / "numpy-1.26.4.tar.gz").read_bytes()).hexdigest()
        != NUMPY_SOURCE_SHA256
    ):
        raise ValueError("NumPy original source archive checksum mismatch")


# Native release preparation. Keep replacements in the existing release entrypoint.
NATIVE_SOURCES = {
    "pillow-11.3.0.tar.gz": "3828ee7586cd0b2091b6209e5ad53e20d0649bbe87164a459d0676e035e8f523",
    "freetype-VER-2-13-3.tar.gz": "bc5c898e4756d373e0d991bab053036c5eb2aa7c0d5c67e8662ddc6da40c4103",
    "libjpeg-turbo-3.1.1.tar.gz": "304165ae11e64ab752e9cfc07c37bfdc87abd0bfe4bc699e59f34036d9c84f72",
    "openmp-15.0.7.src.tar.xz": "3f168d38e7a37b928dcb94b33ce947f75d81eef6fa6a4f9d16b6dc5511c07358",
    "cmake-15.0.7.src.tar.xz": "8986f29b634fdaa9862eedda78513969fe9788301c9f2d938f4c10a3e7a3e7ea",
    "torchvision-0.23.0-source-candidate.tar.gz": "a5008b35513134bc6adfa44902ac1a933d42ddeb131b61f0e054e0f23f902554",
}
TOMLI_WHEEL_SHA256 = "0d85819802132122da43cb86656f8d1f8c6587d54ae7dcaf30e90533028b49fe"
VISION_OPTIONS = {
    key: "0"
    for key in (
        "TORCHVISION_USE_PNG",
        "TORCHVISION_USE_JPEG",
        "TORCHVISION_USE_WEBP",
        "TORCHVISION_USE_NVJPEG",
        "TORCHVISION_USE_FFMPEG",
        "TORCHVISION_USE_VIDEO_CODEC",
    )
}


def native_recipe_digest():
    text = Path(__file__).read_text().split("\n# Native release preparation.", 1)[1]
    return hashlib.sha256(
        text.split("\n# End native preparation.\n", 1)[0].encode()
    ).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_native():
    root = LOCK.parents[2]
    output = LOCK.parent / "build/native-source"
    output.mkdir(parents=True, exist_ok=True)
    original = LOCK.parent / "build/source-delivery"
    for name, expected in NATIVE_SOURCES.items():
        source = (
            original / name
            if name.startswith("torchvision")
            else original / "python" / name
            if name.startswith("pillow")
            else original / "native-src/review" / name
        )
        target = output / name
        if not target.exists():
            shutil.copyfile(source, target)
        if file_digest(target) != expected:
            raise ValueError("Native original source checksum mismatch: " + name)
        with tarfile.open(target) as archive:
            archive.extractall(output, filter="data")
    pure_tomli = original / "native-src/review/tomli-2.4.1-py3-none-any.whl"
    if file_digest(pure_tomli) != TOMLI_WHEEL_SHA256:
        raise ValueError("Official pure-Python Tomli wheel checksum mismatch")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(pure_tomli),
        ],
        check=True,
    )
    tools = LOCK.parent / "build/numpy-build-venv/bin"
    build_python = tools / "python"
    if not build_python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(tools.parent)], check=True)
    build_tools = ["cmake==3.31.6", "ninja==1.11.1.1"]
    subprocess.run(
        [str(build_python), "-m", "pip", "install", "--no-deps", *build_tools],
        check=True,
    )
    shutil.copyfile(pure_tomli, output / pure_tomli.name)
    cmake = str(tools / "cmake")
    env = os.environ.copy()
    env.update(
        MACOSX_DEPLOYMENT_TARGET="14.0",
        SDKROOT=subprocess.check_output(
            ["xcrun", "--show-sdk-path"], text=True
        ).strip(),
    )
    env["PATH"] = str(tools) + os.pathsep + env["PATH"]
    omp = output / "openmp-build"
    omp_args = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0",
        "-DCMAKE_OSX_ARCHITECTURES=arm64",
        "-DLIBOMP_ENABLE_SHARED=ON",
        "-DLIBOMP_OMPT_SUPPORT=OFF",
        "-DOPENMP_ENABLE_LIBOMPTARGET=OFF",
        "-DCMAKE_MODULE_PATH=" + str(output / "cmake-15.0.7.src/Modules"),
    ]
    subprocess.run(
        [cmake, "-S", str(output / "openmp-15.0.7.src"), "-B", str(omp), *omp_args],
        env=env,
        check=True,
    )
    subprocess.run([cmake, "--build", str(omp), "-j4"], env=env, check=True)
    site = Path(importlib.util.find_spec("torch").origin).parent.parent
    target = site / "torch/lib/libomp.dylib"
    shutil.copyfile(omp / "runtime/src/libomp.dylib", target)
    subprocess.run(
        ["install_name_tool", "-id", "@rpath/libomp.dylib", str(target)], check=True
    )
    subprocess.run(["codesign", "--force", "--sign", "-", str(target)], check=True)
    # RECORD describes the installed replacement, not the former wheel bytes.
    record_path = Path(importlib.metadata.distribution("torch")._path) / "RECORD"
    rows = list(csv.reader(io.StringIO(record_path.read_text())))
    relative = "torch/lib/libomp.dylib"
    for row in rows:
        if row[0] == relative:
            row[1:] = [
                "sha256="
                + base64.urlsafe_b64encode(hashlib.sha256(target.read_bytes()).digest())
                .rstrip(b"=")
                .decode(),
                str(target.stat().st_size),
            ]
    stream = io.StringIO()
    csv.writer(stream, lineterminator="\n").writerows(rows)
    record_path.write_text(stream.getvalue())
    vision = output / "torchvision"
    env.update(MAX_JOBS="4", BUILD_VERSION="0.23.0", **VISION_OPTIONS)
    wheels = output / "wheels"
    wheels.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            str(vision),
            "--wheel-dir",
            str(wheels),
        ],
        env=env,
        check=True,
    )
    wheel = next(wheels.glob("torchvision-0.23.0-*.whl"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(wheel),
        ],
        check=True,
    )
    prefix = output / "image-prefix"
    common = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0",
        "-DCMAKE_OSX_ARCHITECTURES=arm64",
        "-DCMAKE_INSTALL_PREFIX=" + str(prefix),
    ]
    image_args = {
        "jpeg": ["-DENABLE_SHARED=OFF", "-DENABLE_STATIC=ON", "-DWITH_TURBOJPEG=OFF"],
        "freetype": [
            "-DBUILD_SHARED_LIBS=OFF",
            "-DFT_DISABLE_BROTLI=ON",
            "-DFT_DISABLE_PNG=ON",
            "-DFT_DISABLE_HARFBUZZ=ON",
            "-DFT_DISABLE_BZIP2=ON",
        ],
    }
    for name, directory in [
        ("jpeg", "libjpeg-turbo-3.1.1"),
        ("freetype", "freetype-VER-2-13-3"),
    ]:
        build = output / (name + "-build")
        subprocess.run(
            [
                cmake,
                "-S",
                str(output / directory),
                "-B",
                str(build),
                *common,
                *image_args[name],
            ],
            env=env,
            check=True,
        )
        subprocess.run([cmake, "--build", str(build), "-j4"], env=env, check=True)
        subprocess.run([cmake, "--install", str(build)], env=env, check=True)
    image_env = env.copy()
    image_env.update(
        CFLAGS="-I" + str(prefix / "include"),
        LDFLAGS="-L" + str(prefix / "lib") + " -L" + env["SDKROOT"] + "/usr/lib",
        JPEG_ROOT=str(prefix),
        FREETYPE_ROOT=str(prefix),
        ZLIB_ROOT=env["SDKROOT"] + "/usr",
    )
    pillow_options = [
        "platform-guessing=disable",
        "jpeg=enable",
        "zlib=enable",
        "freetype=enable",
    ] + [
        key + "=disable"
        for key in [
            "tiff",
            "raqm",
            "lcms",
            "webp",
            "jpeg2000",
            "imagequant",
            "xcb",
            "avif",
        ]
    ]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            str(output / "pillow-11.3.0"),
            "--wheel-dir",
            str(wheels),
            *["--config-settings=" + item for item in pillow_options],
        ],
        env=image_env,
        check=True,
    )
    pillow_wheel = next(wheels.glob("pillow-11.3.0-*.whl"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(pillow_wheel),
        ],
        check=True,
    )
    notice = (output / "openmp-15.0.7.src/LICENSE.TXT").read_text()
    notice += "\n\n--- torchvision BSD ---\n" + (vision / "LICENSE").read_text()
    notice += (
        "\n\n--- vendored giflib (including upstream modifications) ---\n"
        + (vision / "torchvision/csrc/io/image/cpu/giflib/README").read_text()
    )
    notice += (
        "\n\n--- OpenBSD reallocarray ---\n"
        + (vision / "torchvision/csrc/io/image/cpu/giflib/openbsd-reallocarray.c")
        .read_text()
        .split("#include", 1)[0]
    )
    notice += "\n\n--- Pillow ---\n" + (output / "pillow-11.3.0/LICENSE").read_text()
    notice += "\n\nPortions of this software are copyright © 1996-2024 The FreeType Project (www.freetype.org). All rights reserved. FreeType is distributed under the FreeType License (FTL) option.\n"
    notice += (
        "\n--- FreeType FTL ---\n"
        + (output / "freetype-VER-2-13-3/docs/FTL.TXT").read_text()
    )
    notice += (
        "\n--- FreeType embedded third-party terms ---\n"
        + (output / "freetype-VER-2-13-3/LICENSE.TXT").read_text()
    )
    freetype = output / "freetype-VER-2-13-3"
    for path in sorted(
        [*freetype.joinpath("src").rglob("*"), *freetype.joinpath("include").rglob("*")]
    ):
        if path.suffix in {".c", ".h"}:
            comments = re.findall(
                r"/\*.*?\*/", path.read_text(errors="replace"), re.DOTALL
            )
            retained = [text for text in comments if "copyright" in text.lower()]
            if retained:
                notice += (
                    "\n--- "
                    + path.relative_to(output).as_posix()
                    + " ---\n"
                    + "\n".join(retained)
                )
    for name in ["src/bdf/README", "src/pcf/README"]:
        notice += "\n--- FreeType " + name + " ---\n" + (freetype / name).read_text()
    notice += (
        "\nThis software is based in part on the work of the Independent JPEG Group.\n"
    )
    for name in ["LICENSE.md", "README.ijg", "simd/arm/aarch64/jsimd_neon.S"]:
        text = (output / "libjpeg-turbo-3.1.1" / name).read_text()
        if name.endswith(".S"):
            text = text.split("*/", 1)[0] + "*/"
        notice += "\n--- libjpeg-turbo " + name + " ---\n" + text
    (output / "NOTICE.txt").write_text(notice)
    paths = [
        site / "torch/lib/libomp.dylib",
        *sorted((site / "torchvision").glob("*.so")),
        *sorted((site / "PIL").glob("*.so")),
    ]
    record = {
        "sources": NATIVE_SOURCES,
        "recipeSha256": native_recipe_digest(),
        "visionOptions": VISION_OPTIONS,
        "openmpArgs": omp_args,
        "compiler": subprocess.check_output(["clang", "--version"], text=True).strip(),
        "sdk": subprocess.check_output(
            ["xcrun", "--show-sdk-version"], text=True
        ).strip(),
        "buildTools": build_tools,
        "purePythonTomliWheelSha256": TOMLI_WHEEL_SHA256,
        "cmakeVersion": subprocess.check_output(
            [cmake, "--version"], text=True
        ).strip(),
        "visionWheelSha256": file_digest(wheel),
        "pillowWheelSha256": file_digest(pillow_wheel),
        "pillowOptions": pillow_options,
        "imageArgs": image_args,
        "binaries": {p.relative_to(site).as_posix(): file_digest(p) for p in paths},
        "noticeSha256": file_digest(output / "NOTICE.txt"),
    }
    (output / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    with tarfile.open(output / "native-source-delivery.tar.gz", "w:gz") as archive:
        for name in [
            *NATIVE_SOURCES,
            pure_tomli.name,
            "NOTICE.txt",
            "build-record.json",
        ]:
            archive.add(output / name, arcname="native-source/" + name)
        archive.add(
            Path(__file__), arcname="native-source/verify-python-release-lock.py"
        )
        archive.add(
            root / "scripts/build-macos-prerelease.sh",
            arcname="native-source/build-macos-prerelease.sh",
        )


def verify_native(site: Path, source: Path):
    record = json.loads((source / "build-record.json").read_text())
    if (
        record.get("sources") != NATIVE_SOURCES
        or record.get("recipeSha256") != native_recipe_digest()
    ):
        raise ValueError("Native source pins or preparation recipe changed")
    if record.get("visionOptions") != VISION_OPTIONS:
        raise ValueError("torchvision optional codecs must be disabled")
    paths = [
        site / "torch/lib/libomp.dylib",
        *sorted((site / "torchvision").glob("*.so")),
        *sorted((site / "PIL").glob("*.so")),
    ]
    if (
        set(record["binaries"]) != {p.relative_to(site).as_posix() for p in paths}
        or len(paths) < 5
    ):
        raise ValueError("Native replacement binary coverage differs")
    if any((site / "tomli").glob("*.so")):
        raise ValueError("Release Tomli must use its original pure-Python wheel")
    if any((site / "torchvision").rglob("*.dylib")) or any(
        (site / "PIL").rglob("*.dylib")
    ):
        raise ValueError("torchvision contains optional bundled libraries")
    for path in paths:
        if file_digest(path) != record["binaries"][path.relative_to(site).as_posix()]:
            raise ValueError("Native replacement binary differs from source build")
        links = subprocess.check_output(
            ["otool", "-L", str(path)], text=True
        ).splitlines()[1:]
        for line in links:
            link = line.strip().split(" (", 1)[0]
            if not link.startswith(
                (
                    "/usr/lib/",
                    "/System/Library/",
                    "@rpath/libtorch",
                    "@rpath/libc10",
                    "@rpath/libomp",
                )
            ):
                raise ValueError(
                    "Native replacement links a development or codec library"
                )
    for name, expected in NATIVE_SOURCES.items():
        if file_digest(source / name) != expected:
            raise ValueError("Native original source archive changed")
    if file_digest(source / "NOTICE.txt") != record["noticeSha256"]:
        raise ValueError("Native replacement notices changed")


# End native preparation.


def main() -> int:
    if sys.argv[1:] == ["--prepare-native"]:
        prepare_native()
        return 0
    errors = []
    try:
        import torch

        if sys.argv[1:] != ["--numpy-only"]:
            verify_native(
                Path(torch.__file__).parent.parent, LOCK.parent / "build/native-source"
            )
    except (ValueError, KeyError, OSError, IndexError) as error:
        errors.append(str(error))
    try:
        import numpy

        verify_numpy(
            Path(numpy.__file__).parent,
            LOCK.parent / "build/numpy-source",
            numpy.__config__.CONFIG,
        )
    except (ValueError, KeyError, OSError, IndexError) as error:
        errors.append(str(error))
    if sys.argv[1:] == ["--numpy-only"]:
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
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
