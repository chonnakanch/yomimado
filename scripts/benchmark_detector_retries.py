"""Compare the current OCR pipeline with Git and an optional no-tiles ablation.

Loads the baseline pipeline from Git, shares warmed models, alternates profile
order and retains every output. No server, model downloads or release changes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from benchmark_macos_onnx import pipeline_metrics
from benchmark_scan_pipeline import TimedModel, detection_score, pipeline_text_score
from dev_lindera_service import configure

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fixtures(source, output, font):
    from PIL import Image, ImageDraw, ImageFont

    reference = json.loads((source / "comparison.json").read_text())
    expected = {
        case["fixture"]: case["expected"] for case in reference["geometryAccuracy"]
    }
    images = {name: (source / (name + ".png")).read_bytes() for name in expected}
    for size in (14, 24, 40):
        name = f"sparse-page-{size}"
        image = Image.new("RGB", (960, 1100), "white")
        draw = ImageDraw.Draw(image)
        text = "学校へ"
        selected_font = ImageFont.truetype(str(font), size)
        bounds = draw.textbbox((40, 40), text, font=selected_font)
        draw.text((40, 40), text, font=selected_font, fill="black")
        expected[name] = [
            {"text": text, "box": list(bounds), "orientation": "horizontal"}
        ]
        image.save(output / (name + ".png"))
        images[name] = (output / (name + ".png")).read_bytes()
    name = "blank-large"
    Image.new("RGB", (960, 1100), (230, 230, 230)).save(output / (name + ".png"))
    images[name] = (output / (name + ".png")).read_bytes()
    expected[name] = []
    return images, expected


def boxes(regions):
    result = []
    for region in regions:
        xs, ys = (
            [point["x"] for point in region["polygon"]],
            [point["y"] for point in region["polygon"]],
        )
        result.append(
            {
                "box": [min(xs), min(ys), max(xs), max(ys)],
                "orientation": region["orientation"],
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="7cf0154")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "services/ocr/build/lindera-experiment-20261017/scan-benchmark",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "services/ocr/build/detector-priority4-20261018",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--skip-no-tiles",
        action="store_true",
        help="Compare only baseline and current pipeline, retaining normal tile retries",
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("Requires positive repeats")
    env = configure(ROOT, dict(os.environ))
    os.environ.update(env)
    sys.path[:0] = env["PYTHONPATH"].split(os.pathsep)
    import cv2
    import torch
    from app.pipeline import real_ocr

    args.output.mkdir(parents=True, exist_ok=True)
    original = subprocess.check_output(
        [
            "rtk",
            "proxy",
            "git",
            "show",
            args.baseline_ref + ":services/ocr/app/pipeline/real_ocr.py",
        ],
        cwd=ROOT,
    )
    baseline_path = args.output / "baseline_real_ocr.py"
    if baseline_path.exists() and baseline_path.read_bytes() != original:
        raise ValueError("Existing baseline snapshot differs")
    baseline_path.write_bytes(original)
    spec = importlib.util.spec_from_file_location("baseline_pipeline", baseline_path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    images, expected = fixtures(args.fixtures, args.output, args.font)
    detector, recognizer = real_ocr._models(*real_ocr._configured_paths())
    forward = TimedModel(detector.net)
    detector.net = forward
    detector, recognizer = TimedModel(detector, True), TimedModel(recognizer)
    import inference

    refinement = TimedModel(inference.refine_mask)
    profiles = (
        ("baseline", "optimized")
        if args.skip_no_tiles
        else ("baseline", "optimized", "no-tiles")
    )
    samples, outputs = (
        [],
        {profile: {} for profile in profiles},
    )
    with (
        patch.object(real_ocr, "_models", return_value=(detector, recognizer)),
        patch.object(baseline, "_models", return_value=(detector, recognizer)),
        patch.object(inference, "refine_mask", refinement),
    ):
        baseline.recognize_with_models(images["small-horizontal"])
        for name, image in images.items():
            for repeat in range(args.repeats):
                order = list(outputs) if repeat % 2 == 0 else list(reversed(outputs))
                for profile in order:
                    for model in (detector, recognizer, forward, refinement):
                        model.reset()
                    module = real_ocr if profile == "optimized" else baseline
                    with (
                        patch.object(baseline, "_retry_tiles", return_value=[])
                        if profile == "no-tiles"
                        else patch.object(
                            baseline, "_retry_tiles", baseline._retry_tiles
                        )
                    ):
                        started = time.perf_counter()
                        result = module.recognize_with_models(image)
                        elapsed = (time.perf_counter() - started) * 1000
                    payload = result.model_dump(exclude_none=True)
                    if name in outputs[profile] and outputs[profile][name] != payload:
                        raise RuntimeError(
                            "Repeated outputs changed: " + profile + "/" + name
                        )
                    outputs[profile][name] = payload
                    samples.append(
                        {
                            "profile": profile,
                            "fixture": name,
                            "repeat": repeat,
                            "scanMs": elapsed,
                            "detectMs": sum(detector.durations),
                            "recognizeMs": sum(recognizer.durations),
                            "forwardMs": sum(forward.durations),
                            "refineMs": sum(refinement.durations),
                            "detectCalls": len(detector.durations),
                            "recognizeCalls": len(recognizer.durations),
                        }
                    )
            print("Measured " + name, flush=True)
    summary = {}
    for profile, values in outputs.items():
        selected = [sample for sample in samples if sample["profile"] == profile]
        text = [
            {"fixture": name} | pipeline_text_score(expected[name], payload["regions"])
            for name, payload in values.items()
        ]
        summary[profile] = {
            "scans": len(selected),
            "medianMs": {
                key: statistics.median(sample[key] for sample in selected)
                for key in (
                    "scanMs",
                    "detectMs",
                    "recognizeMs",
                    "forwardMs",
                    "refineMs",
                )
            },
            "perFixture": {
                name: {
                    key: statistics.median(
                        sample[key] for sample in selected if sample["fixture"] == name
                    )
                    for key in (
                        "scanMs",
                        "detectMs",
                        "recognizeMs",
                        "detectCalls",
                        "recognizeCalls",
                    )
                }
                for name in values
            },
            "changedFixtures": [
                name for name in values if values[name] != outputs["baseline"][name]
            ],
            "pipelineText": pipeline_metrics(text),
            "geometry": {
                name: detection_score(expected[name], boxes(payload["regions"]))
                for name, payload in values.items()
            },
            "textCases": text,
        }
    report = {
        "scope": "Shared warmed source models; sequential alternating profiles; synthetic images only",
        "baselineRef": args.baseline_ref,
        "baselineSha256": digest(baseline_path),
        "candidateSha256": digest(ROOT / "services/ocr/app/pipeline/real_ocr.py"),
        "benchmarkSha256": digest(Path(__file__)),
        "fontSha256": digest(args.font),
        "fixtureSha256": {
            name: hashlib.sha256(image).hexdigest() for name, image in images.items()
        },
        "metadata": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torchThreads": torch.get_num_threads(),
            "opencv": cv2.__version__,
            "opencvThreads": cv2.getNumThreads(),
            "parallelFramework": next(
                line.strip()
                for line in cv2.getBuildInformation().splitlines()
                if "Parallel framework" in line
            ),
        },
        "expected": expected,
        "summary": summary,
        "samples": samples,
        "outputs": outputs,
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                name: {
                    key: value
                    for key, value in data.items()
                    if key not in ("perFixture", "geometry", "textCases")
                }
                for name, data in summary.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
