"""Pinned dictionary staging must reject changed or unsafe resources."""

import hashlib
import io
import json
import tarfile
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import prepare_lindera as resource


class LinderaPreparationTests(unittest.TestCase):
    def test_rebuild_verifies_source_output_and_preserves_existing_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, software = root / "input.tar.gz", root / "software.tar.gz"
            for archive, files in (
                (source, {"ipadic/data.csv": b"source"}),
                (
                    software,
                    {"software/metadata.json": b"{}", "software/NOTICE": b"notice"},
                ),
            ):
                with tarfile.open(archive, "w:gz") as bundle:
                    for name, raw in files.items():
                        info = tarfile.TarInfo(name)
                        info.size = len(raw)
                        bundle.addfile(info, io.BytesIO(raw))
            pins = {
                "version": "6.0.0",
                "source": {"sha256": resource.digest(software)},
                "dictionarySource": {
                    "sha256": resource.digest(source),
                    "root": "ipadic",
                    "metadata": "software/metadata.json",
                    "notice": "software/NOTICE",
                },
                "dictionary": {
                    "files": {
                        "dict.words": hashlib.sha256(b"words").hexdigest(),
                        "NOTICE.txt": hashlib.sha256(b"notice").hexdigest(),
                    }
                },
            }

            def build(_source, destination, _metadata):
                Path(destination).mkdir()
                (Path(destination) / "dict.words").write_bytes(b"words")

            builder = types.SimpleNamespace(
                build_dictionary=build,
                Metadata=types.SimpleNamespace(from_json_file=lambda path: path),
            )
            target = root / "result"
            with (
                patch.dict("sys.modules", lindera=builder),
                patch.object(resource, "version", return_value="6.0.0"),
            ):
                resource.rebuild(source, software, target, pins)
                self.assertEqual((target / "NOTICE.txt").read_bytes(), b"notice")
                with self.assertRaisesRegex(ValueError, "must be new"):
                    resource.rebuild(source, software, target, pins)
                pins["dictionary"]["files"]["dict.words"] = "0" * 64
                with self.assertRaisesRegex(RuntimeError, "checksum"):
                    resource.rebuild(source, software, root / "bad-output", pins)
                self.assertFalse((root / "bad-output").exists())
                source.write_bytes(b"changed source")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    resource.rebuild(source, software, root / "bad-source", pins)

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
