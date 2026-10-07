"""Verify source archive integrity and exact supplemental notice coverage."""

import base64
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import windows_notices as notices


class WindowsNoticeTests(unittest.TestCase):
    def test_existing_npm_archive_must_match_locked_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.tgz"
            path.write_bytes(b"original archive")
            entry = {
                "resolved": "https://registry.npmjs.org/package/-/package.tgz",
                "integrity": "sha512-"
                + base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode(),
            }
            self.assertEqual(notices.npm_source(entry, path), notices.digest(path))
            path.write_bytes(b"changed archive")
            with self.assertRaisesRegex(ValueError, "integrity differs"):
                notices.npm_source(entry, path)

    def test_unpinned_registry_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unpinned"):
            notices.npm_source(
                {"resolved": "https://example.com/source", "integrity": "sha256-eA=="},
                Path("unused"),
            )

    def test_supplement_text_is_verified_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            copied = notices.supplement("lgpl-2.1", target / "ok")
            self.assertTrue(copied)
            with (
                patch.object(notices, "digest", return_value="changed"),
                self.assertRaisesRegex(ValueError, "hash differs"),
            ):
                notices.supplement("lgpl-2.1", target / "bad")
            self.assertFalse((target / "bad").exists())


if __name__ == "__main__":
    unittest.main()
