"""Offline checks for JLPT data provenance and reproducible transformation."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import prepare_jlpt as jlpt


class JlptDataTests(unittest.TestCase):
    def fixture(self, directory, records):
        source = Path(directory)
        files = []
        for index, (level, expression, reading) in enumerate(records):
            content = json.dumps(
                [
                    [
                        expression,
                        "freq",
                        {"reading": reading, "frequency": {"displayValue": level}},
                    ]
                ]
            ).encode()
            name = f"bank-{index}.json"
            (source / name).write_bytes(content)
            files.append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "level": level,
                }
            )
        return {
            "source": "https://example.invalid/data",
            "revision": "test",
            "files": files,
            "entryCount": len(records),
        }

    def test_retained_sources_reproduce_every_bundled_label_and_license(self):
        pins = json.loads((jlpt.SOURCE / "sources.json").read_text())
        output = jlpt.generate(jlpt.SOURCE, pins)
        self.assertEqual(output, jlpt.OUTPUT.read_bytes())
        self.assertEqual(hashlib.sha256(output).hexdigest(), pins["outputSha256"])
        self.assertEqual(len(json.loads(output)["levels"]), 8113)
        self.assertEqual(
            (jlpt.SOURCE / "LICENSE.txt").read_bytes(),
            (jlpt.OUTPUT.parent / "LICENSE.txt").read_bytes(),
        )

    def test_normalized_readings_keep_homographs_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            pins = self.fixture(
                directory,
                [
                    ("N5", "学校", "ｶﾞｯｺｳ"),
                    ("N5", "上手", "じょうず"),
                    ("N1", "上手", "うわて"),
                ],
            )
            levels = json.loads(jlpt.generate(Path(directory), pins))["levels"]
            self.assertEqual(
                levels,
                {"学校\0がっこう": "N5", "上手\0じょうず": "N5", "上手\0うわて": "N1"},
            )

    def test_changed_input_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            pins = self.fixture(directory, [("N5", "学校", "がっこう")])
            (Path(directory) / "bank-0.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                jlpt.generate(Path(directory), pins)

    def test_conflicting_normalized_levels_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            pins = self.fixture(
                directory, [("N5", "学校", "がっこう"), ("N4", "学校", "ガッコウ")]
            )
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                jlpt.generate(Path(directory), pins)

    def test_invalid_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            pins = self.fixture(directory, [("N0", "学校", "がっこう")])
            with self.assertRaisesRegex(ValueError, "Invalid JLPT source level"):
                jlpt.generate(Path(directory), pins)

    def test_source_path_cannot_escape_reviewed_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            pins = self.fixture(directory, [("N5", "学校", "がっこう")])
            pins["files"][0]["path"] = "../outside.json"
            with self.assertRaisesRegex(ValueError, "escapes"):
                jlpt.generate(Path(directory), pins)


if __name__ == "__main__":
    unittest.main()
