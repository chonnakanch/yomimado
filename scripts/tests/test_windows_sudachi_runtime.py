"""Bind tokenizer sources to the reviewed lock and original notices."""

import copy
import tempfile
import unittest
from pathlib import Path

import windows_sudachi_runtime as sudachi


class SudachiSourceTests(unittest.TestCase):
    def test_retained_lock_requires_complete_original_crates(self):
        inputs = sudachi.read_json(sudachi.MANIFEST)
        sudachi.validate_inputs(inputs, sudachi.LOCK)
        for mutation in ("missing", "changed", "duplicate", "notices"):
            changed = copy.deepcopy(inputs)
            if mutation == "missing":
                changed["crates"].pop()
            elif mutation == "changed":
                changed["crates"][0]["sha256"] = "0" * 64
            elif mutation == "duplicate":
                changed["crates"].append(changed["crates"][0])
            else:
                changed["crates"][0]["noticeHashes"] = {}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                sudachi.validate_inputs(changed, sudachi.LOCK)

    def test_lock_and_manifest_updates_cannot_change_silently(self):
        inputs = sudachi.read_json(sudachi.MANIFEST)
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "Cargo.lock"
            lock.write_bytes(sudachi.LOCK.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "lock differs"):
                sudachi.validate_inputs(inputs, lock)
        for path, content in (
            ("../outside.toml", None),
            ("Cargo.toml", "altered manifest"),
        ):
            changed = copy.deepcopy(inputs)
            changed["manifestUpdates"][0]["path"] = path
            if content is not None:
                changed["manifestUpdates"][0]["content"] = content
            with self.subTest(path=path), self.assertRaises(ValueError):
                sudachi.validate_inputs(changed, sudachi.LOCK)


if __name__ == "__main__":
    unittest.main()
