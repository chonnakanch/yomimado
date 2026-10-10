"""Replacement must bind the actual native build before deleting wheel inputs."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import windows_opencv_runtime as runtime


class OpenCvRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.audit = Path(self.temporary.name) / "audit"
        self.audit.mkdir()
        self.binary = self.audit / "cmake-build/cv2.cp311-win_amd64.pyd"
        self.binary.parent.mkdir()
        self.binary.write_bytes(b"synthetic native checksum fixture")
        for name in ("CMakeCache.txt", "compile_commands.json"):
            (self.audit / name).write_text("retained compiler input")
        self.record = {
            "passed": True,
            "commit": "revision",
            "inputs": runtime.read_json(
                runtime.ROOT / "docs/windows-opencv-build-inputs.json"
            ),
            "recipeSha256": runtime.digest(
                runtime.ROOT / "scripts/build-opencv-windows.py"
            ),
            "probeSha256": runtime.digest(
                runtime.ROOT / "scripts/opencv-windows-probe.py"
            ),
            "options": ["-DWITH_IPP=OFF", "-DBUILD_WITH_STATIC_CRT=OFF"],
            "releaseDllRuntimeCompileCommands": 648,
            "cmakeCacheSha256": runtime.digest(self.audit / "CMakeCache.txt"),
            "compileCommandsSha256": runtime.digest(
                self.audit / "compile_commands.json"
            ),
            "native": {"sha256": runtime.digest(self.binary)},
        }
        self.package = Path(self.temporary.name) / "cv2"
        self.package.mkdir()
        self.old = self.package / "cv2.cp37-win_amd64.pyd"
        self.old.write_bytes(b"old wheel extension")
        (self.package / "__init__.py").write_text("from . import gapi\n")
        (self.package / "gapi").mkdir()
        (self.package / "gapi/__init__.py").write_text("raise RuntimeError('G-API')\n")
        (self.package / "LICENSE.txt").write_bytes(b"original notice\r\n")
        for patcher in (
            patch.object(runtime, "AUDIT", self.audit),
            patch.object(runtime, "BUILD", Path(self.temporary.name) / "build"),
            patch.object(runtime.subprocess, "check_output", return_value="revision\n"),
            patch.object(runtime, "pe_info", return_value={"machine": "0x8664"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write_record()

    def write_record(self):
        runtime.write_json(self.audit / "build-verification.json", self.record)

    def test_changed_build_inputs_cannot_replace_original_extension(self):
        for field, value in (
            ("commit", "other"),
            ("passed", False),
            ("options", ["-DWITH_IPP=ON"]),
            ("recipeSha256", "0" * 64),
            ("releaseDllRuntimeCompileCommands", 0),
        ):
            original = self.record[field]
            self.record[field] = value
            self.write_record()
            with self.assertRaisesRegex(ValueError, "incomplete"):
                runtime.replace()
            self.assertTrue(self.old.is_file())
            self.record[field] = original

    def test_modified_native_or_compile_evidence_is_rejected(self):
        self.binary.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "extension differs"):
            runtime.verified_build()
        self.binary.write_bytes(b"synthetic native checksum fixture")
        (self.audit / "compile_commands.json").write_text("changed")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.verified_build()

    def test_replacement_preserves_source_abi_name_and_records_original_hash(self):
        old_hash = runtime.digest(self.old)
        with patch.object(runtime.importlib.metadata, "distribution") as dist:
            dist.return_value.locate_file.return_value = self.package
            runtime.replace()
        self.assertFalse(self.old.exists())
        self.assertEqual(
            runtime.digest(self.package.parent / self.binary.name),
            runtime.digest(self.binary),
        )
        self.assertFalse((self.package / "__init__.py").exists())
        self.assertFalse((self.package / "gapi").exists())
        self.assertEqual(
            (self.package / "LICENSE.txt").read_bytes(), b"original notice\r\n"
        )
        record = runtime.read_json(runtime.BUILD / "windows-opencv-replacement.json")
        self.assertEqual(record["originalWheelExtensionSha256"], old_hash)
        self.assertIn("gapi/__init__.py", record["removedWheelPythonSha256"])
        self.assertEqual(
            record["preservedWheelNoticesSha256"]["LICENSE.txt"],
            runtime.digest(self.package / "LICENSE.txt"),
        )
        self.assertFalse(record["publicDistributionApproved"])

    def test_notice_manifest_cannot_escape_delivery_directory(self):
        self.record["noticeHashes"] = {"../escape": "0" * 64}
        self.write_record()
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            runtime.retain(Path(self.temporary.name) / "resources")

    def test_nested_notice_and_preferred_source_are_retained_without_changes(self):
        notice = self.audit / "notices/opencv/LICENSE"
        notice.parent.mkdir(parents=True)
        notice.write_bytes(b"original nested notice\r\n")
        self.record["noticeHashes"] = {"opencv/LICENSE": runtime.digest(notice)}
        archive = self.audit / "inputs/source.tar.gz"
        archive.parent.mkdir()
        archive.write_bytes(b"synthetic preferred source archive")
        self.record["inputs"]["source"] = {
            "filename": archive.name,
            "sha256": runtime.digest(archive),
        }
        runtime.write_json(runtime.BUILD / "windows-opencv-replacement.json", {})
        self.write_record()
        resources = Path(self.temporary.name) / "resources"
        with patch.object(
            runtime, "verified_build", return_value=(self.record, self.binary)
        ):
            runtime.retain(resources)
        self.assertEqual(
            (resources / "notices/source-built-opencv/opencv/LICENSE").read_bytes(),
            notice.read_bytes(),
        )
        self.assertEqual(
            (runtime.BUILD / "sources/source-built-opencv/source.tar.gz").read_bytes(),
            archive.read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
