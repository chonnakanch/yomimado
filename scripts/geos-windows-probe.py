"""Synthetic geometry and actual DLL-loading checks for an isolated frozen probe."""

from __future__ import annotations

import ctypes
import hashlib
import json
import platform
import sys
from ctypes import wintypes
from pathlib import Path


def geos_modules() -> list[dict]:
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
        if path.name.lower().startswith("geos"):
            records.append(
                {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return sorted(records, key=lambda item: item["path"].lower())


def main() -> None:
    import numpy as np
    import shapely
    from shapely.affinity import rotate
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import nearest_points, unary_union
    from shapely.prepared import prep

    if sys.platform != "win32" or platform.machine().lower() != "amd64":
        raise ValueError("Requires native Windows x64 execution")
    if shapely.__version__ != "2.0.7" or shapely.geos_version_string != "3.11.4":
        raise ValueError("Unexpected Shapely/GEOS version")
    first, second = box(0, 0, 10, 20), box(5, 10, 15, 30)
    intersection = first.intersection(second)
    union = unary_union([first, second])
    assert intersection.area == 50 and intersection.bounds == (5, 10, 10, 20)
    assert union.area == 350 and union.bounds == (0, 0, 15, 30)
    assert first.difference(second).area == 150
    assert prep(first).contains(Point(3, 4))
    assert not prep(first).contains(Point(30, 40))
    rotated = rotate(first, 30)
    assert abs(rotated.minimum_rotated_rectangle.area - 200) < 1e-9
    repaired = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]).buffer(0)
    assert repaired.is_valid and repaired.area == 1
    near_a, near_b = nearest_points(first, Point(20, 10))
    assert near_a.distance(near_b) == 10
    geometries = np.array([first, second], dtype=object)
    assert shapely.area(geometries).tolist() == [200, 200]
    assert shapely.intersects(geometries, box(7, 12, 8, 13)).tolist() == [True, True]
    assert shapely.from_wkb(shapely.to_wkb(union)).equals(union)
    result = {
        "passed": True,
        "frozen": bool(getattr(sys, "frozen", False)),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
        "fingerprint": {
            "intersection": intersection.normalize().wkt,
            "union": union.normalize().wkt,
            "repair": repaired.normalize().wkt,
        },
        "loadedGeos": geos_modules(),
    }
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
