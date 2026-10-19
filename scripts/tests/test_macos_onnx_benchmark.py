import pytest
from benchmark_macos_onnx import pipeline_metrics, summarize
from benchmark_scan_pipeline import pipeline_text_score


def test_pipeline_metrics_include_text_outside_the_reference_locations():
    expected = [{"text": "学校", "box": [0, 0, 10, 10], "orientation": "horizontal"}]
    regions = [
        {"text": "学校", "polygon": [{"x": 0, "y": 0}, {"x": 10, "y": 10}]},
        {"text": "余分", "polygon": [{"x": 20, "y": 20}, {"x": 30, "y": 30}]},
    ]
    score = pipeline_metrics([pipeline_text_score(expected, regions)])
    assert score["exact"] == 1
    assert score["edits"] == 2
    assert score["characterErrorRate"] == 1.0


def test_blank_images_do_not_claim_a_character_accuracy_percentage():
    score = pipeline_metrics([pipeline_text_score([], [])])
    assert score["characters"] == 0
    assert score["edits"] == 0
    assert score["characterErrorRate"] is None


def test_comparison_rejects_different_fixture_bytes_between_processes():
    with pytest.raises(ValueError, match="same fixture bytes"):
        summarize(
            [{"inputHashes": {"page": "first"}}, {"inputHashes": {"page": "changed"}}]
        )
