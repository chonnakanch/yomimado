from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

scripts = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location(
    "benchmark_scan_pipeline", scripts / "benchmark_scan_pipeline.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AccuracyMetricsTests(unittest.TestCase):
    def test_pipeline_scores_dropped_characters(self):
        expected = [
            {"text": "学校へ", "box": [0, 0, 30, 10], "orientation": "horizontal"}
        ]
        region = {"text": "学校", "polygon": [{"x": 0, "y": 0}, {"x": 20, "y": 10}]}
        score = module.pipeline_text_score(expected, [region])
        self.assertEqual(
            (score["edits"], score["characters"], score["exact"]), (1, 3, 0)
        )

    def test_split_predictions_can_reconstruct_correct_reference(self):
        expected = [
            {"text": "学校へ", "box": [0, 0, 30, 10], "orientation": "horizontal"}
        ]
        regions = [
            {"text": "へ", "polygon": [{"x": 20, "y": 0}, {"x": 30, "y": 10}]},
            {"text": "学校", "polygon": [{"x": 0, "y": 0}, {"x": 20, "y": 10}]},
        ]
        score = module.pipeline_text_score(expected, regions)
        self.assertEqual((score["edits"], score["exact"]), (0, 1))

    def test_unmatched_predictions_count_as_insertions(self):
        region = {"text": "猫", "polygon": [{"x": 0, "y": 0}, {"x": 20, "y": 10}]}
        score = module.pipeline_text_score([], [region])
        self.assertEqual(score["edits"], 1)
        self.assertEqual(score["extraPredictions"], ["猫"])

    def test_geometry_matches_and_duplicate_predictions_are_not_double_counted(self):
        region = {"box": [10, 10, 30, 90], "orientation": "vertical"}
        score = module.detection_score([region], [region, region])
        self.assertEqual(
            score,
            {
                "truePositive": 1,
                "falsePositive": 1,
                "falseNegative": 0,
                "correctOrientation": 1,
            },
        )

    def test_missing_text_and_blank_image_false_positives_are_counted(self):
        region = {"box": [10, 10, 30, 90], "orientation": "vertical"}
        self.assertEqual(module.detection_score([region], [])["falseNegative"], 1)
        self.assertEqual(module.detection_score([], [region])["falsePositive"], 1)

    def test_orientation_mismatch_is_separate_from_location_match(self):
        expected = {"box": [0, 0, 20, 50], "orientation": "vertical"}
        score = module.detection_score(
            [expected], [expected | {"orientation": "horizontal"}]
        )
        self.assertEqual(score["truePositive"], 1)
        self.assertEqual(score["correctOrientation"], 0)

    def test_iou_and_unicode_character_error_distance(self):
        self.assertEqual(module.iou([0, 0, 10, 10], [10, 0, 20, 10]), 0)
        self.assertEqual(module.iou([0, 0, 10, 10], [0, 0, 10, 10]), 1)
        self.assertEqual(module.edit_distance("学校へ", "学校"), 1)
        self.assertEqual(module.edit_distance("🙂学校", "🙂学校"), 0)
        self.assertEqual(module.edit_distance("学校", "会社"), 2)


if __name__ == "__main__":
    unittest.main()
