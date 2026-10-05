"""Verify native license supplements survive generated package notices."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "macos_notices", Path(__file__).parents[1] / "generate-macos-notices.py"
)
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)


class NoticeSupplementTests(unittest.TestCase):
    def test_numpy_preserves_wheel_notice_and_adds_full_lgpl(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            original = "licenses/python/numpy-1.26.4/LICENSE.txt"
            component = {
                "name": "numpy",
                "version": "1.26.4",
                "noticeFiles": [original],
            }
            notices.supplement_python_notices(output, component)
            self.assertEqual(component["noticeFiles"][0], original)
            self.assertEqual(len(component["noticeFiles"]), 2)
            full = (output / component["noticeFiles"][1]).read_text()
            self.assertIn("Version 2.1, February 1999", full)
            self.assertIn("END OF TERMS AND CONDITIONS", full)

    def test_tampered_supplement_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fake.txt").write_text("tampered license")
            (root / "sources.json").write_text(
                json.dumps(
                    {"lgpl-2.1": {"files": [{"path": "fake.txt", "sha256": "wrong"}]}}
                )
            )
            with (
                patch.object(notices, "UPSTREAM", root),
                self.assertRaisesRegex(ValueError, "checksum mismatch"),
            ):
                notices.supplement_python_notices(
                    root, {"name": "numpy", "version": "1.26.4", "noticeFiles": []}
                )


if __name__ == "__main__":
    unittest.main()
