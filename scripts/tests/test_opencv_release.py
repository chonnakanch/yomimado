"""Exercise rejection of upstream/video-enabled OpenCV release inputs."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import opencv_release as release


class OpenCVReleaseTests(unittest.TestCase):
    def information(self, modules=None, extra=""):
        return (
            "  To be built: "
            + " ".join(sorted(modules or release.MODULES))
            + "\n  3rdparty dependencies: libprotobuf libjpeg-turbo libpng zlib\n"
            + extra
        )

    def test_image_onnx_modules_are_accepted(self):
        release.verify_build_information(self.information())

    def test_video_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected OpenCV modules"):
            release.verify_build_information(
                self.information(release.MODULES | {"videoio"})
            )

    def test_ffmpeg_backend_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "video backend enabled"):
            release.verify_build_information(self.information(extra="  FFMPEG: YES\n"))

    def test_unknown_information_is_rejected(self):
        with self.assertRaises(ValueError):
            release.verify_build_information("")

    def test_unreviewed_static_dependency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "static dependencies"):
            release.verify_build_information(
                self.information().replace("zlib", "zlib extra-library")
            )

    def test_upstream_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance mismatch: version"):
            release.verify_record({"version": "4.11.0.86"})

    def test_modified_recipe_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance mismatch: cmakeOptions"):
            release.verify_record(
                {
                    "version": release.VERSION,
                    "sourceSha256": release.SOURCE_SHA256,
                    "cmakeOptions": [],
                }
            )

    def test_missing_binary_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "binary provenance"):
            release.verify_record(
                {
                    "version": release.VERSION,
                    "sourceSha256": release.SOURCE_SHA256,
                    "cmakeOptions": release.OPTIONS,
                    "noticeSources": release.NOTICES,
                }
            )

    def test_codec_names_are_rejected_without_false_positive(self):
        for name in (
            "libavcodec.61.dylib",
            "libx265.212.dylib",
            "libgnutls.30.dylib",
            "libswscale.dylib",
        ):
            self.assertIsNotNone(release.VIDEO_LIBRARY.match(name))
        self.assertIsNone(release.VIDEO_LIBRARY.match("libpng16.dylib"))


if __name__ == "__main__":
    unittest.main()
