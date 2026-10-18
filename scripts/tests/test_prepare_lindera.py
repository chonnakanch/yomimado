"""Pinned dictionary staging must reject changed or unsafe resources."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import prepare_lindera as resource


class LinderaPreparationTests(unittest.TestCase):
    def archive(self, root, files):
        archive = root / "dictionary.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for name, data in files.items():
                bundle.writestr(name, data)
        pins = {
            "dictionary": {
                "sha256": resource.digest(archive),
                "files": {"dict.words": hashlib.sha256(b"words").hexdigest()},
            }
        }
        return archive, pins

    def test_stages_verified_files_and_reuses_only_an_identical_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, pins = self.archive(root, {"lindera-ipadic/dict.words": b"words"})
            destination = root / "staged"
            resource.stage(archive, destination, pins)
            resource.stage(archive, destination, pins)
            (destination / "dict.words").write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                resource.stage(archive, destination, pins)
            self.assertEqual((destination / "dict.words").read_bytes(), b"changed")

    def test_rejects_changed_archives_and_unexpected_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, pins = self.archive(root, {"../dict.words": b"words"})
            with self.assertRaisesRegex(ValueError, "membership"):
                resource.stage(archive, root / "rejected", pins)
            archive.write_bytes(b"changed archive")
            with self.assertRaisesRegex(ValueError, "checksum"):
                resource.stage(archive, root / "rejected", pins)
            self.assertFalse((root / "rejected").exists())

    def test_rejects_corrupt_extracted_members_without_partial_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, pins = self.archive(
                root, {"lindera-ipadic/dict.words": b"corrupt"}
            )
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                resource.stage(archive, root / "rejected", pins)
            self.assertFalse((root / "rejected").exists())

    def test_release_and_runtime_dictionary_pins_match_experiment(self):
        runtime = json.loads(resource.INPUTS.read_text())
        experiment = json.loads(
            (resource.SERVICE / "lindera-experiment-inputs.json").read_text()
        )
        self.assertEqual(runtime["dictionary"], experiment["dictionary"])
        windows = json.loads((resource.SERVICE / "windows-inputs.json").read_text())
        names = {p["name"] for p in windows["packages"]}
        self.assertIn("lindera", names)
        self.assertNotIn("SudachiPy", names)
        self.assertNotIn("SudachiDict-core", names)

    def test_source_archive_uses_exact_pin_instead_of_missing_pypi_sdist(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "macos_lindera_sources", resource.ROOT / "scripts/prepare-macos-sources.py"
        )
        sources = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sources)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)

            def download(url, target, expected, algorithm, hosts):
                target.parent.mkdir(parents=True)
                target.write_bytes(b"source")

            with patch.object(sources, "download", side_effect=download) as fetch:
                record = sources.python_archive(
                    {"name": "lindera", "version": "6.0.0", "ecosystem": "python"},
                    output,
                )
            self.assertIn("codeload.github.com", record["origin"])
            self.assertEqual(
                fetch.call_args.args[2],
                json.loads(resource.INPUTS.read_text())["source"]["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
