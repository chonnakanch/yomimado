import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import translation_component as component
from app.translation_resources import TranslationResources


class ComponentTests(unittest.TestCase):
    def test_model_is_separated_from_installer_and_installs_from_verified_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resources = root / "resources"
            model = resources / "assets/opus-mt-ja-en"
            model.mkdir(parents=True)
            pins = {}
            for name, data in {
                "README.md": b"Apache model card",
                "config.json": b"{}",
                "pytorch_model.bin": b"synthetic weights",
            }.items():
                path = model / name
                path.write_bytes(data)
                pins["opus-mt-ja-en/" + name] = component.digest(path)
            with patch.object(component, "pins", return_value=pins):
                archive = component.prepare(
                    resources, root / "downloads", "1.0.0", "torch"
                )
                self.assertFalse(model.exists())
                self.assertEqual(component.verify_omissions(resources), pins)
                manifest = resources / "notices/translation-component.json"
                manager = TranslationResources(manifest, root / "user-models")
                manager.install_archive(archive, root / "stage")
                self.assertEqual(
                    (manager.model_path() / "pytorch_model.bin").read_bytes(),
                    b"synthetic weights",
                )
                record = json.loads(manifest.read_text())
                record["excludedAssets"]["JMdict_e.gz"] = "a" * 64
                manifest.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "exclusion differs"):
                    component.verify_omissions(resources)

    def test_ocr_resource_verifier_rejects_dictionaries_and_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            internal = runtime / "_internal"
            internal.mkdir()
            for name in (
                "unidic_lite",
                "fugashi",
                "unidic_lite-1.0.8.dist-info",
                "sudachipy",
                "sudachidict_core",
                "SudachiPy-0.6.10.dist-info",
            ):
                path = internal / name
                path.mkdir()
                with self.assertRaisesRegex(ValueError, "Unused OCR"):
                    component.verify_ocr_runtime(runtime)
                path.rmdir()

    def test_prune_removes_obsolete_metadata_but_preserves_code_and_lindera(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            internal = runtime / "_internal"
            internal.mkdir()
            obsolete = (
                "unidic_lite-1.0.8.dist-info",
                "fugashi-1.5.2.dist-info",
                "SudachiPy-0.6.10.dist-info",
                "sudachidict_core-20250515.dist-info",
            )
            retained = ("lindera-6.0.0.dist-info", "torch-2.8.0.dist-info", "sudachipy")
            for name in obsolete + retained:
                (internal / name).mkdir()
                (internal / name / "METADATA").write_text("fixture")
            component.prune_ocr_metadata(runtime)
            self.assertEqual({path.name for path in internal.iterdir()}, set(retained))
            # Cleanup must not conceal an accidentally collected old binding.
            with self.assertRaisesRegex(ValueError, "Unused OCR"):
                component.verify_ocr_runtime(runtime)
            (internal / "sudachipy/METADATA").unlink()
            (internal / "sudachipy").rmdir()
            component.verify_ocr_runtime(runtime)
