"""Boundary cases for the isolated inference migration experiment."""

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from check_onnx_probe import failure_annotation
from onnx_detector_probe import non_max_suppression
from onnx_generation import Policy, beam_search, generation_scores


class NmsTests(unittest.TestCase):
    def test_overlap_suppresses_only_same_class_and_preserves_input(self):
        prediction = np.asarray(
            [
                [
                    [10, 10, 10, 10, 0.9, 0.9, 0.1],
                    [10, 10, 10, 10, 0.8, 0.9, 0.1],
                    [10, 10, 10, 10, 0.7, 0.1, 0.9],
                ]
            ],
            dtype=np.float32,
        )
        original = prediction.copy()
        result = non_max_suppression(prediction, 0.4, 0.35)[0]
        np.testing.assert_array_equal(prediction, original)
        self.assertEqual(result[:, 5].tolist(), [0, 1])
        np.testing.assert_allclose(result[:, 4], [0.81, 0.63])

    def test_object_times_class_threshold_is_strict(self):
        prediction = np.asarray(
            [[[5, 5, 2, 2, 1, 0.4], [10, 10, 2, 2, 0.9, 0.5]]], dtype=np.float32
        )
        result = non_max_suppression(prediction, 0.4)[0]
        self.assertEqual(len(result), 1)
        np.testing.assert_allclose(result[0, :4], [9, 9, 11, 11])

    def test_iou_equal_to_limit_is_retained(self):
        prediction = np.asarray(
            [[[5, 5, 2, 2, 1, 0.9], [5, 5, 2, 2, 1, 0.8]]], dtype=np.float32
        )
        self.assertEqual(len(non_max_suppression(prediction, 0.4, 1)[0]), 2)

    def test_empty_batch_and_invalid_threshold(self):
        prediction = np.empty((1, 0, 7), dtype=np.float32)
        self.assertEqual(non_max_suppression(prediction)[0].shape, (0, 6))
        with self.assertRaises(ValueError):
            non_max_suppression(prediction, iou_thres=1.1)

    def test_three_hundred_output_cap(self):
        prediction = np.asarray(
            [[[10 * i, 0, 1, 1, 1, 0.9] for i in range(305)]], dtype=np.float32
        )
        self.assertEqual(len(non_max_suppression(prediction)[0]), 300)

    def test_random_overlaps_match_torchvision_cpu_operator(self):
        import torch
        from torchvision.ops import nms

        random = np.random.default_rng(20261010)
        for _ in range(20):
            prediction = random.uniform(0, 1, (1, 100, 8)).astype(np.float32)
            prediction[:, :, :2] *= 100
            prediction[:, :, 2:4] *= 40
            result = non_max_suppression(prediction, 0.4, 0.35)[0]
            raw = prediction[0]
            conf = raw[:, 5:] * raw[:, 4:5]
            cls = conf.argmax(axis=1)
            scores = conf[np.arange(len(raw)), cls]
            boxes = np.column_stack(
                (raw[:, :2] - raw[:, 2:4] / 2, raw[:, :2] + raw[:, 2:4] / 2)
            )
            expected = np.column_stack((boxes, scores, cls)).astype(np.float32)
            expected = expected[(raw[:, 4] > 0.4) & (scores > 0.4)]
            selected = nms(
                torch.from_numpy(expected[:, :4] + expected[:, 5:6] * 4096),
                torch.from_numpy(expected[:, 4]),
                0.35,
            ).numpy()
            np.testing.assert_array_equal(result, expected[selected])


class GenerationTests(unittest.TestCase):
    def test_repeated_ngram_and_banned_token_are_blocked(self):
        ids = np.array([[2, 4, 5, 4, 5]])
        scores = generation_scores(
            np.zeros((1, 7)), ids, Policy(2, 3, 2, 20, no_repeat_ngram=3, banned=(6,))
        )
        self.assertTrue(np.isneginf(scores[0, 4]))
        self.assertTrue(np.isneginf(scores[0, 6]))
        self.assertTrue(np.isfinite(scores[0, 5]))

    def test_marian_forced_eos_and_renormalization(self):
        scores = generation_scores(
            np.ones((1, 5)),
            np.array([[4, 2]]),
            Policy(4, 0, 2, 3, forced_eos=True, renormalize=True),
        )
        self.assertEqual(scores[0, 0], 0)
        self.assertTrue(np.isneginf(scores[0, 1:]).all())

    def test_beam_search_stops_at_eos_and_ranks_completed_sequences(self):
        def step(ids):
            logits = np.full((len(ids), 5), -30.0)
            if ids.shape[1] == 1:
                logits[:, 1], logits[:, 2] = 4, 3
            else:
                logits[:, 3] = 5
            return logits

        self.assertEqual(
            beam_search(step, Policy(0, 3, 2, 10, early_stopping=True)), [0, 1, 3]
        )

    def test_invalid_generation_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_search(lambda ids: np.zeros((len(ids), 5)), Policy(0, 3, 0, 2))


class WorkflowTests(unittest.TestCase):
    def test_failure_details_escape_github_annotation_control_characters(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
        ):
            failure_annotation("synthetic failure: 25%\r\nnext line")
        self.assertIn("25%25%0D%0Anext line", stdout.getvalue())
        self.assertIn("synthetic failure", stderr.getvalue())

    def test_evidence_upload_does_not_include_models_or_sources(self):
        workflow = (
            Path(__file__).parents[2] / ".github/workflows/windows-onnx-prototype.yml"
        ).read_text()
        artifact = workflow.split("name: windows-onnx-feasibility-evidence", 1)[1]
        paths = artifact.split("path: |", 1)[1].split("if-no-files-found", 1)[0]
        for line in paths.splitlines():
            if line.strip():
                self.assertTrue(line.strip().endswith((".log", ".json")))
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("actions: write", workflow)
        pins = json.loads(
            (Path(__file__).parents[1] / "onnx-probe-inputs.json").read_text()
        )
        for pin in pins:
            self.assertTrue(pin["filename"].endswith(".whl"))
            self.assertEqual(len(pin["sha256"]), 64)
            self.assertTrue(pin["url"].startswith("https://files.pythonhosted.org/"))


if __name__ == "__main__":
    unittest.main()
