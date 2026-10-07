"""Reject altered Windows inputs, leaked models, and changed installed binaries."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location(
    "windows_release", Path(__file__).parents[1] / "windows_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class WindowsReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_actual_lock_matches_and_only_cpu_torch_is_selected(self):
        manifest = release.read_json(release.SERVICE / "windows-inputs.json")
        release.validate_lock(manifest)
        manifest["packages"][0]["version"] = "unreviewed"
        with self.assertRaisesRegex(ValueError, "manifest differ"):
            release.validate_lock(manifest)

    def test_changed_cpu_wheel_url_is_rejected(self):
        manifest = release.read_json(release.SERVICE / "windows-inputs.json")
        next(e for e in manifest["packages"] if e["name"] == "torch")["url"] = (
            "https://pypi.org/torch.whl"
        )
        with self.assertRaisesRegex(ValueError, "CPU Torch"):
            release.validate_lock(manifest)

    def test_detector_and_unapproved_weights_are_rejected_at_any_depth(self):
        for suffix in release.FORBIDDEN:
            path = self.root / ("model" + suffix)
            path.write_bytes(b"weights")
            with self.assertRaisesRegex(ValueError, "weights"):
                release.assert_no_detector(self.root)
            path.unlink()
        alias = self.root / "comictextdetector.pt.renamed"
        alias.write_bytes(b"weights")
        with self.assertRaisesRegex(ValueError, "weights"):
            release.assert_no_detector(self.root)

    def test_source_symlinks_are_rejected(self):
        (self.root / "alias").symlink_to(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "symlink"):
            release.assert_no_detector(self.root)

    def test_changed_download_is_not_promoted_to_a_new_pin(self):
        source = self.root / "source"
        source.write_bytes(b"changed bytes")
        target = self.root / "target"
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            release.fetch({"url": source.as_uri(), "sha256": "0" * 64}, target)
        self.assertFalse(target.exists())
        self.assertFalse(target.with_name("target.download").exists())

    def resources(self):
        notices = self.root / "notices"
        notices.mkdir()
        for name in [
            "LICENSE",
            "MODEL_CREDITS.md",
            "ASSET_NOTICES.md",
            "project-revision.txt",
            "windows-inputs.json",
            "windows-assets.json",
            "distribution.json",
        ]:
            (notices / name).write_text("test")
        runtime = self.root / "runtime"
        runtime.mkdir()
        exe = runtime / "yomimado-ocr.exe"
        exe.write_bytes(b"MZsynthetic")
        release.write_json(
            notices / "windows-inventory.json",
            {
                "binaries": [
                    {
                        "path": "runtime/yomimado-ocr.exe",
                        "sha256": release.digest(exe),
                        "imports": [],
                    }
                ]
            },
        )
        return exe

    def verify(self, machine="0x8664"):
        with (
            patch.object(
                release,
                "read_json",
                side_effect=lambda p: (
                    [] if p.name == "windows-assets.json" else json.loads(p.read_text())
                ),
            ),
            patch.object(
                release, "pe_info", return_value={"machine": machine, "imports": []}
            ),
        ):
            return release.verify_resources(self.root)

    def test_installed_native_hash_is_bound_to_inventory(self):
        exe = self.resources()
        self.verify()
        exe.write_bytes(b"MZchanged")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            self.verify()

    def test_mixed_pe_architecture_is_rejected(self):
        self.resources()
        with self.assertRaisesRegex(ValueError, "architecture"):
            self.verify("0x14c")

    def test_extra_dll_is_rejected_even_if_x64(self):
        self.resources()
        (self.root / "runtime/extra.dll").write_bytes(b"MZextra")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            self.verify()

    def test_native_names_with_non_pe_content_are_rejected(self):
        (self.root / "invalid.pyd").write_bytes(b"not a PE")
        with self.assertRaisesRegex(ValueError, "not a PE"):
            list(release.native_files(self.root))


if __name__ == "__main__":
    unittest.main()
