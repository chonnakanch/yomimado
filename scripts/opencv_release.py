"""Validate the image/ONNX-only macOS OpenCV release input."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path

VERSION = "4.11.0.86+yomimado.1"
SOURCE_NAME = "opencv-python-4.11.0.86.tar.gz"
SOURCE_URL = (
    "https://files.pythonhosted.org/packages/17/06/"
    "68c27a523103dad5837dc5b87e71285280c4f098c60e4fe8a8db6486ab09/" + SOURCE_NAME
)
SOURCE_SHA256 = "03d60ccae62304860d232272e4a4fda93c39d595780cb40b161b310244b736a4"
TOOLS = [
    "pip==26.0.1",
    "setuptools==80.9.0",
    "wheel==0.48.0",
    "scikit-build==0.18.1",
    "cmake==3.31.6",
    "ninja==1.11.1.4",
    "numpy==1.26.4",
    "packaging==26.3",
    "distro==1.9.0",
    "tomli==2.4.1",
]
OPTIONS = [
    "-DWITH_ADE=OFF",
    "-DBUILD_opencv_gapi=OFF",
    "-DCMAKE_OSX_ARCHITECTURES=arm64",
    "-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0",
    "-DBUILD_LIST=core,imgproc,imgcodecs,calib3d,dnn,highgui,python3",
    "-DWITH_FFMPEG=OFF",
    "-DWITH_GSTREAMER=OFF",
    "-DWITH_AVFOUNDATION=OFF",
    "-DBUILD_opencv_videoio=OFF",
    "-DBUILD_opencv_highgui=ON",
    "-DWITH_QT=OFF",
    "-DWITH_GTK=OFF",
    "-DWITH_WIN32UI=OFF",
    "-DWITH_OPENCL=OFF",
    "-DWITH_IPP=OFF",
    "-DWITH_ITT=OFF",
    "-DWITH_CAROTENE=OFF",
    "-DWITH_EIGEN=OFF",
    "-DWITH_LAPACK=OFF",
    "-DWITH_TBB=OFF",
    "-DWITH_OPENMP=OFF",
    "-DWITH_OPENVX=OFF",
    "-DWITH_FLATBUFFERS=OFF",
    "-DOPENCV_DNN_TFLITE=OFF",
    "-DWITH_PROTOBUF=ON",
    "-DBUILD_PROTOBUF=ON",
    "-DWITH_PNG=ON",
    "-DBUILD_PNG=ON",
    "-DWITH_JPEG=ON",
    "-DBUILD_JPEG=ON",
    "-DBUILD_ZLIB=ON",
    "-DWITH_TIFF=OFF",
    "-DWITH_WEBP=OFF",
    "-DWITH_OPENJPEG=OFF",
    "-DWITH_JASPER=OFF",
    "-DWITH_OPENEXR=OFF",
    "-DWITH_AVIF=OFF",
    "-DWITH_GDAL=OFF",
    "-DWITH_GDCM=OFF",
    "-DWITH_QUIRC=OFF",
    "-DOPENCV_ENABLE_NONFREE=OFF",
    "-DOPENCV_PYTHON_SKIP_DETECTION=OFF",
    "-DPYTHON3_LIMITED_API=ON",
]
NOTICES = [
    "opencv/LICENSE",
    "opencv/3rdparty/libjpeg-turbo/LICENSE.md",
    "opencv/3rdparty/libjpeg-turbo/README.ijg",
    "opencv/3rdparty/libpng/LICENSE",
    "opencv/3rdparty/zlib/LICENSE",
    "opencv/3rdparty/protobuf/LICENSE",
    "opencv/modules/core/3rdparty/SoftFloat/COPYING.txt",
    "opencv/modules/features2d/3rdparty/mscr/chi_table_LICENSE.txt",
]

# These should never return to the release runtime through another wheel.
VIDEO_LIBRARY = re.compile(
    r"^(?:lib)?(?:avcodec|avformat|avutil|avdevice|avfilter|swscale|swresample|postproc|x264|x265|gnutls)(?:[.-]|$)",
    re.IGNORECASE,
)
MODULES = {
    "calib3d",
    "core",
    "dnn",
    "features2d",
    "flann",
    "imgcodecs",
    "imgproc",
    "highgui",
    "python3",
}


def verify_record(record: dict) -> None:
    for field, expected in (
        ("version", VERSION),
        ("sourceSha256", SOURCE_SHA256),
        ("cmakeOptions", OPTIONS),
        ("noticeSources", NOTICES),
    ):
        if record.get(field) != expected:
            raise ValueError(f"OpenCV build provenance mismatch: {field}")
    if not re.fullmatch(r"[a-f0-9]{64}", record.get("binarySha256", "")):
        raise ValueError("Missing OpenCV binary provenance")
    verify_build_information(record.get("buildInformation", ""))


def verify_build_information(information: str) -> None:
    modules = re.search(r"^\s*To be built:\s*(.+)$", information, re.MULTILINE)
    if not modules or set(modules[1].split()) != MODULES:
        raise ValueError("Unexpected OpenCV modules; image/ONNX-only build required")
    dependencies = re.search(
        r"^\s*3rdparty dependencies:\s*(.+)$", information, re.MULTILINE
    )
    if not dependencies or set(dependencies[1].split()) != {
        "libprotobuf",
        "libjpeg-turbo",
        "libpng",
        "zlib",
    }:
        raise ValueError("Unexpected OpenCV static dependencies")
    if re.search(
        r"^\s*(?:FFMPEG|GStreamer|AVFoundation):\s*YES",
        information,
        re.MULTILINE | re.IGNORECASE,
    ):
        raise ValueError("OpenCV video backend enabled")


def verify_installed(record_path: Path) -> dict:
    import cv2

    record = json.loads(record_path.read_text())
    verify_record(record)
    if importlib.metadata.version("opencv-python") != VERSION:
        raise ValueError("Install the YomiMado custom OpenCV wheel before bundling")
    (binary,) = Path(cv2.__file__).parent.glob("*.so")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != record["binarySha256"]:
        raise ValueError("Installed OpenCV binary does not match its build record")
    notice = binary.parent / "LICENSE-3RD-PARTY.txt"
    if (
        hashlib.sha256(notice.read_bytes()).hexdigest()
        != record["modifiedFiles"]["LICENSE-3RD-PARTY.txt"]
    ):
        raise ValueError("Installed OpenCV notices do not match its source build")
    information = cv2.getBuildInformation()
    verify_build_information(information)
    if information.strip() != record["buildInformation"].strip():
        raise ValueError("Installed OpenCV build information changed")
    for name in ("VideoCapture", "VideoWriter"):
        if hasattr(cv2, name):
            raise ValueError(f"Unexpected OpenCV video/GUI API: {name}")
    links = subprocess.check_output(["otool", "-L", str(binary)], text=True)
    for line in links.splitlines()[1:]:
        dependency = line.strip().split(" (", 1)[0]
        if not dependency.startswith(("/usr/lib/", "/System/Library/")):
            raise ValueError(f"OpenCV has an external dynamic dependency: {dependency}")
    print(
        "Verified source-built OpenCV: image/ONNX and system-GUI compatibility, no video backends or external dylibs."
    )
    return record


if __name__ == "__main__":
    try:
        verify_installed(Path(sys.argv[1]))
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
