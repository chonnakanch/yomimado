"""Reject unsafe source inputs and incorrect Windows native audit evidence."""

import copy
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parents[1] / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load("opencv_windows", "build-opencv-windows.py")
probe = load("opencv_windows_probe", "opencv-windows-probe.py")


class OpenCVWindowsTests(unittest.TestCase):
    def test_windows_cmake_library_paths_do_not_form_escape_sequences(self):
        self.assertEqual(
            audit.cmake_path(r"D:\a\source with spaces\PCbuild\amd64\python311.lib"),
            "D:/a/source with spaces/PCbuild/amd64/python311.lib",
        )

    def information(self):
        return (
            "To be built: core imgproc imgcodecs calib3d features2d flann dnn highgui python3\n"
            "3rdparty dependencies: libprotobuf libjpeg-turbo libpng zlib\n"
            "OpenCL: NO\nFFMPEG: NO"
        )

    def test_forbidden_static_vendors_and_backends_are_rejected(self):
        audit.verify_information(self.information())
        for info in (
            self.information().replace("zlib", "zlib ippicv"),
            self.information() + "\nIntel IPP: 2021.12.0",
            self.information().replace("OpenCL: NO", "OpenCL: YES"),
            self.information().replace("FFMPEG: NO", "FFMPEG: YES"),
            self.information().replace("python3", "python3 videoio"),
        ):
            with self.subTest(info=info), self.assertRaises(ValueError):
                audit.verify_information(info)

    def test_accepted_cache_must_disable_ipp_and_keep_recorded_linkage(self):
        cache = "\n".join(
            [
                *[key + ":BOOL=OFF" for key in audit.OFF],
                *[key + ":BOOL=ON" for key in audit.ON],
                "CMAKE_BUILD_TYPE:STRING=Release",
                "CMAKE_MSVC_RUNTIME_LIBRARY:STRING=MultiThreadedDLL",
            ]
        )
        audit.verify_cache(cache)
        for wrong in (
            cache.replace("WITH_IPP:BOOL=OFF", "WITH_IPP:BOOL=ON"),
            cache.replace("WITH_IPP_IW:BOOL=OFF", ""),
            cache.replace("MultiThreadedDLL", "MultiThreaded"),
        ):
            with self.subTest(cache=wrong), self.assertRaises(ValueError):
                audit.verify_cache(wrong)

    def test_probe_requires_exact_native_loading_and_detector_execution(self):
        native = Path("/tmp/cv2.pyd")
        report = {
            "passed": True,
            "frozen": True,
            "python": "3.11.17",
            "machine": "AMD64",
            "opencv": "4.11.0",
            "buildInformation": self.information(),
            "loadedOpenCV": [{"path": str(native), "sha256": "a" * 64}],
            "loadedModules": [{"path": "/tmp/python311.dll"}],
            "detectorSha256": probe.DETECTOR_SHA256,
            "detectorOutputs": [
                {"orientation": "horizontal"},
                {"orientation": "vertical"},
            ],
        }
        audit.verify_probe(report, native, True, "a" * 64)
        for key, value in (
            ("frozen", False),
            ("machine", "ARM64"),
            ("python", "3.11.9"),
            ("loadedOpenCV", [{"path": "/tmp/old/cv2.pyd", "sha256": "a" * 64}]),
            ("loadedOpenCV", [{"path": str(native), "sha256": "b" * 64}]),
            ("loadedModules", [{"path": "/tmp/libiomp5md.dll"}]),
            ("detectorSha256", "b" * 64),
            ("detectorOutputs", []),
        ):
            wrong = copy.deepcopy(report)
            wrong[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.verify_probe(wrong, native, True, "a" * 64)

    def test_source_archive_rejects_traversal_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, kind in (
                ("../outside", tarfile.REGTYPE),
                ("opencv-python-4.11.0.86/link", tarfile.SYMTYPE),
            ):
                archive = root / "source.tar"
                with tarfile.open(archive, "w") as tar:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "/tmp/outside"
                    tar.addfile(member, io.BytesIO())
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, "Unsafe"),
                ):
                    audit.extract_source(archive, root / "extracted")
            self.assertFalse((root / "outside").exists())

    def test_synthetic_geometry_has_expected_horizontal_and_vertical_boxes(self):
        # Executes the image operations locally; Windows inference/freeze is separate.
        result = probe.geometry_checks()
        self.assertEqual(
            result["boxes"], [[10, 20, 50, 20, 1000], [100, 10, 20, 70, 1400]]
        )
        self.assertTrue(result["pngRoundTrip"])


if __name__ == "__main__":
    unittest.main()
