"""Reject unbound installer plugin sources and changed template behavior."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_nsis_plugin as plugin


class NsisPluginTests(unittest.TestCase):
    def test_exact_lock_requires_all_original_sources_and_notices(self):
        original = plugin.read_json(plugin.MANIFEST)
        plugin.validate(original)
        for mutation in ("missing", "duplicate", "checksum", "notice", "target"):
            inputs = copy.deepcopy(original)
            if mutation == "missing":
                inputs["crates"].pop()
            elif mutation == "duplicate":
                inputs["crates"].append(inputs["crates"][0])
            elif mutation == "checksum":
                inputs["crates"][0]["sha256"] = "0" * 64
            elif mutation == "notice":
                inputs["crates"][0]["noticeHashes"] = {}
            else:
                inputs["target"] = "x86_64-pc-windows-msvc"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                plugin.validate(inputs)

    def test_lock_bytes_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "Cargo.lock"
            altered.write_bytes(plugin.LOCK.read_bytes() + b"\n")
            with (
                patch.object(plugin, "LOCK", altered),
                self.assertRaisesRegex(ValueError, "lock differs"),
            ):
                plugin.validate(plugin.read_json(plugin.MANIFEST))

    def test_template_preserves_every_other_installation_line(self):
        original = "before\n" + plugin.TEMPLATE_LINE + "\nafter\n"
        directory = Path("/private/tmp/nsis-source-plugin")
        generated = plugin.template(original, directory)
        self.assertEqual(generated.splitlines()[0], "before")
        self.assertEqual(generated.splitlines()[2], "after")
        self.assertIn(directory.resolve().as_posix(), generated)
        for changed in ("unrecognized", original + plugin.TEMPLATE_LINE):
            with self.assertRaises(ValueError):
                plugin.template(changed, directory)
        for unsafe in ("/private/tmp/$PLUGIN", '/private/tmp/"quoted'):
            with self.assertRaises(ValueError):
                plugin.template(original, Path(unsafe))


if __name__ == "__main__":
    unittest.main()
