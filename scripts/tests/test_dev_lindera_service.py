from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "dev_lindera_service",
    Path(__file__).resolve().parents[1] / "dev_lindera_service.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DevelopmentLaunchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        assets = self.root / "apps/desktop/src-tauri/resources/ocr/assets"
        self.inputs = [
            assets / "comic-text-detector/inference.py",
            assets / "manga-ocr-base/pytorch_model.bin",
            assets / "manga-ocr-base/config.json",
            self.root / "services/ocr/local-models/comictextdetector.pt.onnx",
            self.root
            / "services/ocr/build/lindera-experiment-20261017/dictionary/lindera-ipadic/metadata.json",
        ]
        for path in self.inputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")

    def test_full_ui_configuration_includes_ocr_and_learning_inputs(self):
        env = module.configure(self.root, {})
        self.assertEqual(env["YOMIMADO_TOKENIZER"], "lindera")
        self.assertTrue(Path(env["YOMIMADO_DETECTOR_REPO"], "inference.py").is_file())
        self.assertTrue(Path(env["YOMIMADO_DETECTOR_MODEL"]).is_file())
        self.assertTrue(
            Path(env["YOMIMADO_MANGA_OCR_MODEL"], "pytorch_model.bin").is_file()
        )
        self.assertTrue(Path(env["YOMIMADO_JMDICT"]).is_absolute())
        self.assertTrue(Path(env["YOMIMADO_TRANSLATION_MODEL"]).is_absolute())
        self.assertIn("dev-data", env["YOMIMADO_VOCAB_DB"])
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_preserves_explicit_input_paths_and_pythonpath(self):
        alternative = self.root / "my-detector.onnx"
        alternative.write_bytes(b"local detector")
        env = module.configure(
            self.root,
            {"YOMIMADO_DETECTOR_MODEL": str(alternative), "PYTHONPATH": "/local/extra"},
        )
        self.assertEqual(env["YOMIMADO_DETECTOR_MODEL"], str(alternative))
        self.assertTrue(env["PYTHONPATH"].endswith("/local/extra"))

    def test_missing_model_fails_before_demo_service_can_start(self):
        self.inputs[3].unlink()
        with self.assertRaisesRegex(RuntimeError, "detector weights"):
            module.configure(self.root, {})


if __name__ == "__main__":
    unittest.main()
