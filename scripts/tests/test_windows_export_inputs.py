"""Model omission requires bound conversion and successful runtime comparison."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_export_inputs as export


class ExportInputTests(unittest.TestCase):
    def test_prune_retains_only_validated_export_inputs_outside_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "resources"
            build = root / "build"
            service = root / "service"
            service.mkdir()
            pins = []
            for name in sorted(export.WEIGHTS):
                path = resources / "assets" / name
                path.parent.mkdir(parents=True)
                path.write_bytes(name.encode())
                pins.append({"path": name, "sha256": export.digest(path)})
            (service / "windows-assets.json").write_text(json.dumps(pins))
            graphs = {}
            for name in (
                "ocr-encoder",
                "ocr-decoder",
                "translation-encoder",
                "translation-decoder",
            ):
                path = resources / "assets/onnx" / (name + ".onnx")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
                graphs[path] = export.digest(path)
            (resources / "assets/onnx/export.json").write_text("bound conversion")
            comparison = build / "onnx-comparison/comparison.json"
            comparison.parent.mkdir(parents=True)
            result = {
                "ocr": {"horizontal": "学校", "vertical": "学校へ"},
                "translation": {"a": "A", "b": "B", "c": "C"},
                "torchImported": False,
                "cacheSurvivedNewService": True,
            }
            report = {
                "exactOcrParity": True,
                "exactTranslationParity": True,
                "torchAbsentFromOnnxWorker": True,
                "results": {"baseline": result, "onnx": result},
            }
            comparison.write_text(json.dumps(report))
            with (
                patch.object(export, "SERVICE", service),
                patch.object(export, "BUILD", build),
                patch.object(export, "derived_onnx_graphs", return_value=graphs),
            ):
                # No file is moved when any of the original hashes is wrong.
                bad = resources / "assets" / pins[-1]["path"]
                original = bad.read_bytes()
                bad.write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "weight changed"):
                    export.prune(resources)
                self.assertTrue(
                    all((resources / "assets" / p["path"]).exists() for p in pins)
                )
                bad.write_bytes(original)
                export.prune(resources)
                self.assertEqual(export.verify(resources), export.WEIGHTS)
                self.assertTrue(
                    all(
                        (build / "export-only-models" / p["path"]).exists()
                        for p in pins
                    )
                )
                (resources / "assets" / pins[0]["path"]).write_bytes(b"reintroduced")
                with self.assertRaisesRegex(ValueError, "Unbound"):
                    export.verify(resources)

    def test_parity_flags_cannot_cover_different_runtime_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "comparison.json"
            path.write_text(
                json.dumps(
                    {
                        "exactOcrParity": True,
                        "exactTranslationParity": True,
                        "torchAbsentFromOnnxWorker": True,
                        "results": {
                            "baseline": {
                                "ocr": {"horizontal": "different", "vertical": "text"}
                            },
                            "onnx": {
                                "ocr": {"horizontal": "学校", "vertical": "学校へ"},
                                "translation": {"a": "A", "b": "B", "c": "C"},
                            },
                        },
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "incomplete"):
                export.check_comparison(path)


if __name__ == "__main__":
    unittest.main()
