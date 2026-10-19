"""Measure the unchanged OCR pipeline alongside both development tokenizers.

Synthetic, locally rendered fixtures only. No screenshot capture or downloads.
Detector/recognizer adapters are timed in-process without editing production code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from benchmark_lindera_tokenizer import CHECKS
from dev_lindera_service import configure

ROOT = Path(__file__).resolve().parents[1]


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union else 0.0


def detection_score(expected, predicted):
    pairs = sorted(
        (
            (iou(a["box"], b["box"]), i, j)
            for i, a in enumerate(expected)
            for j, b in enumerate(predicted)
        ),
        reverse=True,
    )
    matched_expected, matched_predictions = set(), set()
    aligned = 0
    for overlap, i, j in pairs:
        if overlap < 0.5 or i in matched_expected or j in matched_predictions:
            continue
        matched_expected.add(i)
        matched_predictions.add(j)
        aligned += expected[i]["orientation"] == predicted[j]["orientation"]
    return {
        "truePositive": len(matched_expected),
        "falsePositive": len(predicted) - len(matched_predictions),
        "falseNegative": len(expected) - len(matched_expected),
        "correctOrientation": aligned,
    }


def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for row, left in enumerate(a, 1):
        current = [row]
        for column, right in enumerate(b, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left != right),
                )
            )
        previous = current
    return previous[-1]


def pipeline_text_score(expected, regions):
    """Assign text to known synthetic locations, independently of the 0.5 IoU gate.

    This is benchmark alignment using known layout, not an app reading-order
    algorithm. Split predictions can reconstruct a correct reference string.
    Unmatched predictions count as inserted characters rather than disappearing.
    """
    groups = [[] for _ in expected]
    extras = []
    for region in regions:
        xs, ys = (
            [p["x"] for p in region["polygon"]],
            [p["y"] for p in region["polygon"]],
        )
        box = [min(xs), min(ys), max(xs), max(ys)]
        overlaps = [iou(item["box"], box) for item in expected]
        if not overlaps or max(overlaps) == 0:
            extras.append(region["text"])
            continue
        index = max(range(len(expected)), key=overlaps.__getitem__)
        groups[index].append((box, region["text"]))
    cases = []
    for item, group in zip(expected, groups):
        coordinate = 1 if item["orientation"] == "vertical" else 0
        predicted = "".join(
            text for _, text in sorted(group, key=lambda pair: pair[0][coordinate])
        )
        predicted = "".join(predicted.split())
        reference = "".join(item["text"].split())
        cases.append(
            {
                "reference": reference,
                "predicted": predicted,
                "edits": edit_distance(reference, predicted),
                "characters": len(reference),
                "exact": reference == predicted,
            }
        )
    return {
        "cases": cases,
        "extraPredictions": extras,
        "edits": sum(x["edits"] for x in cases)
        + sum(len("".join(x.split())) for x in extras),
        "characters": sum(x["characters"] for x in cases),
        "exact": sum(x["exact"] for x in cases),
    }


def render_fixtures(font_path: Path):
    from PIL import Image, ImageDraw, ImageFont

    specifications = [
        ("small-horizontal", (240, 100), [("学校へ", (20, 20), False, 40, 0, 0)]),
        ("small-vertical", (100, 240), [("学校へ", (25, 20), True, 40, 0, 0)]),
        (
            "sentence-horizontal",
            (640, 140),
            [("今日は学校に行きます。", (25, 30), False, 40, 0, 0)],
        ),
        (
            "sentence-vertical",
            (140, 600),
            [("無理はダメだよ", (45, 30), True, 40, 0, 0)],
        ),
        ("small-font", (600, 140), [("食べました。", (30, 40), False, 24, 0, 0)]),
        (
            "low-contrast",
            (640, 140),
            [("お兄ちゃん、待って！", (25, 30), False, 40, 140, 0)],
        ),
        (
            "skew-horizontal",
            (640, 160),
            [("今日は学校に行きます。", (25, 35), False, 40, 0, 3)],
        ),
        (
            "mixed-page",
            (960, 1100),
            [
                ("今日は学校に行きます。", (790, 130), True, 40, 0, 0),
                ("無理はダメだよ", (600, 200), True, 40, 0, 0),
                ("食べました。", (90, 860), False, 40, 0, 0),
            ],
        ),
        ("blank", (600, 600), []),
    ]
    fixtures = []
    for name, dimensions, regions in specifications:
        image = Image.new("RGB", dimensions, "white")
        expected = []
        for text, position, vertical, font_size, gray, angle in regions:
            layer = Image.new("RGBA", dimensions, (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            font = ImageFont.truetype(str(font_path), font_size)
            if vertical:
                for index, character in enumerate(text):
                    draw.text(
                        (position[0], position[1] + index * (font_size + 8)),
                        character,
                        font=font,
                        fill=(gray, gray, gray, 255),
                        anchor="lt",
                    )
            else:
                draw.text(
                    position, text, font=font, fill=(gray, gray, gray, 255), anchor="lt"
                )
            if angle:
                layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC)
            bounds = layer.getbbox()
            if bounds is None:
                raise RuntimeError("Synthetic text did not render")
            image.paste(layer, (0, 0), layer)
            expected.append(
                {
                    "text": text,
                    "box": list(bounds),
                    "orientation": "vertical" if vertical else "horizontal",
                }
            )
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
        fixtures.append(
            {
                "name": name,
                "image": image,
                "bytes": encoded.getvalue(),
                "expected": expected,
            }
        )
    return fixtures


class TimedModel:
    def __init__(self, model, detector=False):
        self.model = model
        self.detector = detector
        self.reset()

    def reset(self):
        self.durations = []
        self.first_boxes = []

    def __call__(self, *args, **kwargs):
        start = time.perf_counter()
        result = self.model(*args, **kwargs)
        self.durations.append((time.perf_counter() - start) * 1000)
        if self.detector and len(self.durations) == 1:
            self.first_boxes = [
                {
                    "box": [float(x) for x in block.xyxy],
                    "orientation": "vertical" if block.vertical else "horizontal",
                }
                for block in result[2]
            ]
        return result


def summarize(values):
    return {
        "medianMs": statistics.median(values),
        "p95Ms": sorted(values)[int(0.95 * (len(values) - 1))],
        "samples": len(values),
    }


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    env = configure(ROOT, dict(os.environ))
    os.environ.update(env)
    sys.path[:0] = env["PYTHONPATH"].split(os.pathsep)
    import cv2
    import torch
    from app.pipeline import real_ocr
    from app.tokenizer.provider import get_tokenizer

    args.output.mkdir(parents=True, exist_ok=True)
    fixtures = render_fixtures(args.font)
    start = time.perf_counter()
    detector, recognizer = real_ocr._models(*real_ocr._configured_paths())
    model_load_ms = (time.perf_counter() - start) * 1000
    detector, recognizer = TimedModel(detector, True), TimedModel(recognizer)
    tokenizers, quality = {}, {}
    for profile in ("sudachi", "lindera"):
        os.environ["YOMIMADO_TOKENIZER"] = profile
        tokenizers[profile] = get_tokenizer()
        tokenizers[profile].tokenize("学校")
        quality[profile] = [
            {
                "text": text,
                "passed": any(
                    (x.surface, x.reading, x.dictionaryForm) == (surface, reading, base)
                    for x in tokenizers[profile].tokenize(text)
                ),
            }
            for text, surface, reading, base in CHECKS
        ]
    records = []
    accuracy = []
    references = {}
    with patch.object(real_ocr, "_models", return_value=(detector, recognizer)):
        real_ocr.recognize_with_models(fixtures[0]["bytes"])
        for fixture in fixtures:
            fixture["image"].save(args.output / (fixture["name"] + ".png"))
            for repeat in range(args.repeats):
                order = (
                    ("sudachi", "lindera")
                    if repeat % 2 == 0
                    else ("lindera", "sudachi")
                )
                for profile in order:
                    detector.reset()
                    recognizer.reset()
                    start = time.perf_counter()
                    result = real_ocr.recognize_with_models(fixture["bytes"])
                    scan_ms = (time.perf_counter() - start) * 1000
                    payload = result.model_dump(exclude_none=True)
                    if (
                        fixture["name"] in references
                        and references[fixture["name"]] != payload
                    ):
                        raise RuntimeError(
                            "OCR outputs changed across profiles or repeated scans"
                        )
                    references[fixture["name"]] = payload
                    start = time.perf_counter()
                    for region in result.regions:
                        tokenizers[profile].tokenize(region.text)
                    tokenize_ms = (time.perf_counter() - start) * 1000
                    records.append(
                        {
                            "fixture": fixture["name"],
                            "profile": profile,
                            "repeat": repeat,
                            "scanMs": scan_ms,
                            "detectMs": sum(detector.durations),
                            "recognizeMs": sum(recognizer.durations),
                            "tokenizeAllRegionsMs": tokenize_ms,
                            "detectCalls": len(detector.durations),
                            "recognizeCalls": len(recognizer.durations),
                        }
                    )
                    if repeat == 0 and profile == "sudachi":
                        final_boxes = []
                        for region in result.regions:
                            xs, ys = (
                                [p.x for p in region.polygon],
                                [p.y for p in region.polygon],
                            )
                            final_boxes.append(
                                {
                                    "box": [min(xs), min(ys), max(xs), max(ys)],
                                    "orientation": region.orientation,
                                }
                            )
                        accuracy.append(
                            {
                                "fixture": fixture["name"],
                                "expected": fixture["expected"],
                                "firstPass": detection_score(
                                    fixture["expected"], detector.first_boxes
                                ),
                                "finalRegions": detection_score(
                                    fixture["expected"], final_boxes
                                ),
                            }
                        )
            print("Measured " + fixture["name"], flush=True)
    recognition = []
    for fixture in fixtures:
        for expected in fixture["expected"]:
            x1, y1, x2, y2 = expected["box"]
            crop = fixture["image"].crop(
                (
                    max(0, x1 - 8),
                    max(0, y1 - 8),
                    min(fixture["image"].width, x2 + 8),
                    min(fixture["image"].height, y2 + 8),
                )
            )
            text = recognizer.model(crop)
            reference = "".join(expected["text"].split())
            predicted = "".join(text.split())
            recognition.append(
                {
                    "fixture": fixture["name"],
                    "reference": reference,
                    "predicted": predicted,
                    "edits": edit_distance(reference, predicted),
                    "characters": len(reference),
                    "exact": reference == predicted,
                }
            )
    per_fixture = {
        fixture["name"]: {
            profile: {
                field: summarize(
                    [
                        r[field]
                        for r in records
                        if r["fixture"] == fixture["name"] and r["profile"] == profile
                    ]
                )
                for field in (
                    "scanMs",
                    "detectMs",
                    "recognizeMs",
                    "tokenizeAllRegionsMs",
                )
            }
            for profile in tokenizers
        }
        for fixture in fixtures
    }
    detection = {}
    for stage in ("firstPass", "finalRegions"):
        totals = {
            key: sum(x[stage][key] for x in accuracy)
            for key in (
                "truePositive",
                "falsePositive",
                "falseNegative",
                "correctOrientation",
            )
        }
        tp, fp, fn = (
            totals[x] for x in ("truePositive", "falsePositive", "falseNegative")
        )
        detection[stage] = totals | {
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }
    pipeline_text = [
        {"fixture": fixture["name"]}
        | pipeline_text_score(
            fixture["expected"], references[fixture["name"]]["regions"]
        )
        for fixture in fixtures
    ]
    summary = {
        "sameOcrOutputs": True,
        "fixtures": len(fixtures),
        "scans": len(records),
        "modelLoadMs": model_load_ms,
        "profiles": {
            profile: {
                field: summarize([r[field] for r in records if r["profile"] == profile])
                for field in (
                    "scanMs",
                    "detectMs",
                    "recognizeMs",
                    "tokenizeAllRegionsMs",
                )
            }
            for profile in tokenizers
        },
        "detection": detection,
        "recognition": {
            "crops": len(recognition),
            "exact": sum(x["exact"] for x in recognition),
            "characterErrorRate": sum(x["edits"] for x in recognition)
            / sum(x["characters"] for x in recognition),
        },
        "pipelineText": {
            "regions": sum(len(x["cases"]) for x in pipeline_text),
            "exact": sum(x["exact"] for x in pipeline_text),
            "edits": sum(x["edits"] for x in pipeline_text),
            "characters": sum(x["characters"] for x in pipeline_text),
            "characterErrorRate": sum(x["edits"] for x in pipeline_text)
            / sum(x["characters"] for x in pipeline_text),
        },
        "learningChecks": {
            profile: {"passed": sum(x["passed"] for x in cases), "total": len(cases)}
            for profile, cases in quality.items()
        },
    }
    report = {
        "scope": "source-only synthetic CPU benchmark, not real-manga accuracy or installed-app acceptance",
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "torchThreads": torch.get_num_threads(),
            "opencvThreads": cv2.getNumThreads(),
        },
        "versions": {
            x: importlib.metadata.version(x)
            for x in (
                "torch",
                "transformers",
                "numpy",
                "Pillow",
                "lindera",
                "SudachiPy",
                "SudachiDict-core",
            )
        },
        "inputSha256": {
            "font": digest(args.font),
            "benchmark": digest(Path(__file__)),
            "detector": digest(env["YOMIMADO_DETECTOR_MODEL"]),
            "recognizer": digest(
                Path(env["YOMIMADO_MANGA_OCR_MODEL"]) / "pytorch_model.bin"
            ),
        },
        "summary": summary,
        "perFixture": per_fixture,
        "samples": records,
        "geometryAccuracy": accuracy,
        "recognitionAccuracy": recognition,
        "pipelineTextAccuracy": pipeline_text,
        "learningChecks": quality,
        "ocrOutputs": references,
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
