"""Keep the original export baseline out of the delivered ONNX environment."""

import unittest

import prepare_onnx_probe as probe


class OnnxInputTests(unittest.TestCase):
    def test_reference_numpy_and_torch_never_enter_the_new_runtime(self):
        packages = probe.read_json(probe.ROOT / "services/ocr/windows-inputs.json")[
            "packages"
        ]
        additions = probe.read_json(probe.ROOT / "scripts/onnx-probe-inputs.json")
        baseline = probe.select_packages(packages, additions, baseline=True)
        runtime = probe.select_packages(packages, additions, baseline=False)
        self.assertEqual(
            [p["version"] for p in baseline if p.get("package") == "numpy-baseline"],
            ["1.26.4"],
        )
        self.assertFalse(any(p.get("name") == "numpy" for p in baseline))
        self.assertEqual(
            [p["version"] for p in runtime if p.get("name") == "numpy"], ["2.4.6"]
        )
        self.assertFalse(
            any(
                p.get("package") == "numpy-baseline" or p.get("name") in probe.EXCLUDED
                for p in runtime
            )
        )
        self.assertTrue(any(p.get("name") == "torch" for p in baseline))

    def test_missing_or_duplicate_reference_numpy_is_rejected(self):
        packages = [{"name": "numpy", "version": "2.4.6"}]
        entry = {"package": "numpy-baseline", "version": "1.26.4"}
        for additions in ([], [entry, entry], [{**entry, "version": "2.4.6"}]):
            with self.subTest(additions=additions), self.assertRaises(ValueError):
                probe.select_packages(packages, additions, baseline=True)


if __name__ == "__main__":
    unittest.main()
