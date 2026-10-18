"""Cache correctness at beam selection boundaries, independent of model files."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from onnx_cached_experiment import CachedStep, parent_rows

NAMES = [
    f"{kind}_{layer}_{slot}"
    for layer in range(2)
    for kind, slot in (
        ("self", "key"),
        ("self", "value"),
        ("cross", "key"),
        ("cross", "value"),
    )
]


class FakeSession:
    def __init__(self, cached=False):
        self.cached = cached
        self.feeds = None

    def get_inputs(self):
        return [
            SimpleNamespace(name=name)
            for name in (
                ["input_ids"] + ["past_" + name for name in NAMES]
                if self.cached
                else ["input_ids", "encoder_hidden_states"]
            )
        ]

    def get_outputs(self):
        return [
            SimpleNamespace(name=name)
            for name in ["logits"] + ["present_" + name for name in NAMES]
        ]

    def run(self, unused, feeds):
        self.feeds = feeds
        beams = len(feeds["input_ids"])
        return [np.zeros((beams, 1, 6))] + [
            np.arange(beams).reshape(beams, 1, 1, 1) + index * 10 for index in range(8)
        ]


class CacheTests(unittest.TestCase):
    def test_beams_can_duplicate_drop_and_reorder_parents(self):
        previous = np.array([[2, 1], [2, 3], [2, 4], [2, 5]])
        current = np.array([[2, 5, 6], [2, 3, 7], [2, 3, 8], [2, 1, 9]])
        self.assertEqual(parent_rows(previous, current).tolist(), [3, 1, 1, 0])

    def test_identical_prefixes_can_share_the_same_cache(self):
        previous = np.full((4, 1), 2)
        current = np.array([[2, 1], [2, 3], [2, 4], [2, 5]])
        self.assertEqual(parent_rows(previous, current).tolist(), [0, 0, 0, 0])

    def test_missing_prefix_and_skipped_steps_fail(self):
        for current in (np.array([[3, 4]]), np.array([[2, 3, 4]])):
            with self.assertRaises(ValueError):
                parent_rows(np.array([[2]]), current)

    def test_all_self_and_cross_tensors_follow_parents(self):
        prefill, decoder = FakeSession(), FakeSession(cached=True)
        step = CachedStep(prefill, decoder, np.zeros((1, 197, 768)))
        previous = np.array([[2], [3], [4], [5]])
        step(previous)
        current = np.array([[5, 6], [3, 7], [3, 8], [2, 9]])
        step(current)
        np.testing.assert_array_equal(decoder.feeds["input_ids"], current[:, -1:])
        self.assertNotIn("encoder_hidden_states", decoder.feeds)
        for index, name in enumerate(NAMES):
            self.assertEqual(
                decoder.feeds["past_" + name].ravel().tolist(),
                (np.array([3, 1, 1, 0]) + index * 10).tolist(),
            )
        np.testing.assert_array_equal(previous, [[2], [3], [4], [5]])

    def test_prefill_rejects_a_multi_token_prompt(self):
        step = CachedStep(FakeSession(), FakeSession(True), np.zeros((1, 197, 768)))
        with self.assertRaises(ValueError):
            step(np.array([[2, 3]]))


if __name__ == "__main__":
    unittest.main()
