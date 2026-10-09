"""Original synthetic image/geometry and smoke-only detector inference probe."""

from __future__ import annotations

import ctypes
import hashlib
import json
import platform
import sys
from ctypes import wintypes
from pathlib import Path

DETECTOR_SHA256 = "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f"


def loaded_modules() -> list[dict]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32EnumProcessModules.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.K32GetModuleFileNameExW.argtypes = [
        wintypes.HANDLE,
        wintypes.HMODULE,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    process = kernel.GetCurrentProcess()
    modules = (wintypes.HMODULE * 4096)()
    needed = wintypes.DWORD()
    if not kernel.K32EnumProcessModules(
        process, modules, ctypes.sizeof(modules), ctypes.byref(needed)
    ) or needed.value > ctypes.sizeof(modules):
        raise ctypes.WinError(ctypes.get_last_error())
    records = []
    for handle in modules[: needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        name = ctypes.create_unicode_buffer(32768)
        if not kernel.K32GetModuleFileNameExW(process, handle, name, len(name)):
            raise ctypes.WinError(ctypes.get_last_error())
        path = Path(name.value).resolve()
        records.append(
            {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    return sorted(records, key=lambda item: item["path"].lower())


def geometry_checks() -> dict:
    import cv2
    import numpy as np

    # Horizontal and vertical shapes exercise geometry without third-party artwork.
    mask = np.zeros((100, 160), dtype=np.uint8)
    cv2.rectangle(mask, (10, 20), (59, 39), 255, -1)
    cv2.rectangle(mask, (100, 10), (119, 79), 255, -1)
    _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    boxes = sorted(stats[1:].tolist())
    assert count == 3 and boxes == [[10, 20, 50, 20, 1000], [100, 10, 20, 70, 1400]]
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted(cv2.contourArea(c) for c in contours)
    assert areas == [931.0, 1311.0]
    corners = np.array([[0, 0], [99, 0], [99, 99], [0, 99]], dtype=np.float32)
    matrix, _ = cv2.findHomography(corners, corners + (7, 11))
    transformed = cv2.perspectiveTransform(corners.reshape(1, -1, 2), matrix)
    assert np.allclose(transformed, (corners + (7, 11)).reshape(1, -1, 2))
    bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    encoded, png = cv2.imencode(".png", bgr)
    assert encoded and np.array_equal(cv2.imdecode(png, cv2.IMREAD_COLOR), bgr)
    encoded, jpeg = cv2.imencode(".jpg", bgr)
    assert encoded and cv2.imdecode(jpeg, cv2.IMREAD_COLOR).shape == bgr.shape
    assert callable(cv2.imshow)  # Required import in detector; never opens a GUI here.
    assert not hasattr(cv2, "VideoCapture") and not hasattr(cv2, "VideoWriter")
    return {
        "boxes": boxes,
        "areas": areas,
        "homography": transformed.round(6).tolist(),
        "pngRoundTrip": True,
        "jpegDecode": True,
    }


def main() -> None:
    import cv2
    import numpy as np

    if sys.platform != "win32" or platform.machine().lower() != "amd64":
        raise ValueError("Requires native Windows x64")
    detector, fixtures = Path(sys.argv[2]), Path(sys.argv[3])
    if hashlib.sha256(detector.read_bytes()).hexdigest() != DETECTOR_SHA256:
        raise ValueError("Detector checksum differs")
    cv2.setNumThreads(1)
    geometry = geometry_checks()
    net = cv2.dnn.readNetFromONNX(str(detector))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    results = []
    for orientation in ("horizontal", "vertical"):
        fixture = fixtures / ("windows-ocr-" + orientation + ".png")
        image = cv2.imread(str(fixture))
        assert image is not None
        net.setInput(
            cv2.dnn.blobFromImage(image, scalefactor=1 / 255.0, size=(1024, 1024))
        )
        outputs = net.forward(net.getUnconnectedOutLayersNames())
        assert len(outputs) == 3 and all(
            output.size and np.isfinite(output).all() for output in outputs
        )
        results.append(
            {
                "orientation": orientation,
                "fixtureSha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                "shapes": [list(o.shape) for o in outputs],
                "ranges": [
                    [round(float(o.min()), 6), round(float(o.max()), 6)]
                    for o in outputs
                ],
            }
        )
    modules = loaded_modules()
    report = {
        "passed": True,
        "frozen": bool(getattr(sys, "frozen", False)),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "buildInformation": cv2.getBuildInformation(),
        "geometry": geometry,
        "detectorSha256": DETECTOR_SHA256,
        "detectorOutputs": results,
        "loadedModules": modules,
        "loadedOpenCV": [
            p
            for p in modules
            if Path(p["path"]).suffix.lower() == ".pyd"
            and Path(p["path"]).name.lower().startswith("cv2")
        ],
    }
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
