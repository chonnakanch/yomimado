"""Compare existing CPU Torch and ONNX OCR in isolated macOS source processes.

Uses local synthetic fixtures and pinned exports. Does not change the running
service, production providers, model files or dependency locks.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from benchmark_scan_pipeline import (
    TimedModel,
    detection_score,
    edit_distance,
    pipeline_text_score,
)
from dev_lindera_service import configure

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {
    "torch",
    "torchvision",
    "manga_ocr",
    "unidic",
    "unidic_lite",
    "fugashi",
    "MeCab",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metrics(cases: list[dict]) -> dict:
    characters = sum(case["characters"] for case in cases)
    return {
        "exact": sum(case["exact"] for case in cases),
        "regions": len(cases),
        "edits": sum(case["edits"] for case in cases),
        "characters": characters,
        "characterErrorRate": sum(case["edits"] for case in cases) / characters
        if characters
        else 0,
    }


def pipeline_metrics(items: list[dict]) -> dict:
    result = metrics([case for item in items for case in item["cases"]])
    # Include inserted text outside every reference location, too.
    result["edits"] = sum(item["edits"] for item in items)
    result["characterErrorRate"] = (
        result["edits"] / result["characters"] if result["characters"] else None
    )
    return result


def worker(args):
    import resource

    started = time.perf_counter()
    env = configure(ROOT, dict(os.environ))
    os.environ.update(env)
    sys.path[:0] = env["PYTHONPATH"].split(os.pathsep)
    if args.profile == "onnx":
        os.environ["USE_TORCH"] = "0"

        original_import = builtins.__import__

        def guarded_import(name, *arguments, **keywords):
            if name.split(".")[0] in BLOCKED:
                raise ImportError("Blocked in ONNX investigation: " + name)
            return original_import(name, *arguments, **keywords)

        builtins.__import__ = guarded_import
    import cv2
    from app.pipeline import real_ocr
    from app.tokenizer.provider import get_tokenizer
    from PIL import Image

    reference = json.loads((args.fixtures / "comparison.json").read_text())
    expected = {
        case["fixture"]: case["expected"] for case in reference["geometryAccuracy"]
    }
    fixtures = {
        name: (args.fixtures / (name + ".png")).read_bytes() for name in expected
    }
    metadata = {"platform": platform.platform(), "python": platform.python_version()}
    imported_ms = (time.perf_counter() - started) * 1000
    load_started = time.perf_counter()
    paths = real_ocr._configured_paths()
    if args.profile == "torch":
        import torch

        detector, recognizer = real_ocr._models(*paths)
        metadata.update(
            torch=importlib.metadata.version("torch"),
            torchThreads=torch.get_num_threads(),
        )
    else:
        import onnxruntime as ort
        from onnx_detector import detector_class
        from onnx_runtime import OnnxRecognizer
        from windows_onnx_backend import verified_exports

        verified_exports(args.exports, "ocr")
        detector = detector_class(paths[0])(str(paths[1]))
        recognizer = OnnxRecognizer(paths[2], args.exports)
        metadata.update(
            onnxruntime=ort.__version__,
            availableProviders=ort.get_available_providers(),
            activeProviders=recognizer.encoder.get_providers(),
            ortThreads=recognizer.encoder.get_session_options().intra_op_num_threads,
        )
    load_ms = (time.perf_counter() - load_started) * 1000
    tokenizer = get_tokenizer()
    tokenizer.tokenize("学校で食べました。")
    detector, recognizer = TimedModel(detector, True), TimedModel(recognizer)
    samples, outputs, geometry, text_cases = [], {}, [], []
    with patch.object(real_ocr, "_models", return_value=(detector, recognizer)):
        warm_started = time.perf_counter()
        real_ocr.recognize_with_models(fixtures["small-horizontal"])
        warmup_ms = (time.perf_counter() - warm_started) * 1000
        ready_ms = (time.perf_counter() - started) * 1000
        for name, image in fixtures.items():
            for repeat in range(args.repeats):
                detector.reset()
                recognizer.reset()
                scan_started = time.perf_counter()
                result = real_ocr.recognize_with_models(image)
                elapsed = (time.perf_counter() - scan_started) * 1000
                payload = result.model_dump(exclude_none=True)
                if name in outputs and payload != outputs[name]:
                    raise RuntimeError("Repeated OCR results changed for " + name)
                outputs[name] = payload
                token_started = time.perf_counter()
                for region in result.regions:
                    tokenizer.tokenize(region.text)
                samples.append(
                    {
                        "fixture": name,
                        "repeat": repeat,
                        "scanMs": elapsed,
                        "detectMs": sum(detector.durations),
                        "recognizeMs": sum(recognizer.durations),
                        "detectCalls": len(detector.durations),
                        "recognizeCalls": len(recognizer.durations),
                        "tokenizeMs": (time.perf_counter() - token_started) * 1000,
                    }
                )
                if repeat == 0:
                    boxes = []
                    for region in result.regions:
                        xs, ys = (
                            [point.x for point in region.polygon],
                            [point.y for point in region.polygon],
                        )
                        boxes.append(
                            {
                                "box": [min(xs), min(ys), max(xs), max(ys)],
                                "orientation": region.orientation,
                            }
                        )
                    geometry.append(
                        {
                            "fixture": name,
                            "firstPass": detection_score(
                                expected[name], detector.first_boxes
                            ),
                            "finalRegions": detection_score(expected[name], boxes),
                        }
                    )
                    text_cases.append(
                        {"fixture": name}
                        | pipeline_text_score(expected[name], payload["regions"])
                    )
            print(args.profile + " measured " + name, flush=True)
    recognition = []
    for name, cases in expected.items():
        image = Image.open(args.fixtures / (name + ".png"))
        for case in cases:
            x1, y1, x2, y2 = case["box"]
            predicted = recognizer.model(
                image.crop(
                    (
                        max(0, x1 - 8),
                        max(0, y1 - 8),
                        min(image.width, x2 + 8),
                        min(image.height, y2 + 8),
                    )
                )
            )
            predicted, text = "".join(predicted.split()), "".join(case["text"].split())
            recognition.append(
                {
                    "fixture": name,
                    "reference": text,
                    "predicted": predicted,
                    "characters": len(text),
                    "edits": edit_distance(text, predicted),
                    "exact": text == predicted,
                }
            )
    metadata.update(
        opencv=cv2.__version__,
        opencvThreads=cv2.getNumThreads(),
        transformers=importlib.metadata.version("transformers"),
        numpy=importlib.metadata.version("numpy"),
        lindera=importlib.metadata.version("lindera"),
        blockedModulesLoaded=sorted(
            {name.split(".")[0] for name in sys.modules} & BLOCKED
        ),
    )
    result = {
        "benchmarkSha256": digest(Path(__file__)),
        "profile": args.profile,
        "metadata": metadata,
        "samples": samples,
        "processSetupMs": {
            "imports": imported_ms,
            "modelLoad": load_ms,
            "warmupScan": warmup_ms,
            "throughReady": ready_ms,
        },
        "peakRssBytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "outputs": outputs,
        "geometry": geometry,
        "pipelineTextCases": text_cases,
        "recognitionCases": recognition,
        "pipelineText": pipeline_metrics(text_cases),
        "recognition": metrics(recognition),
        "inputHashes": {
            name: hashlib.sha256(data).hexdigest() for name, data in fixtures.items()
        },
    }
    args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def summarize(runs: list[dict]) -> dict:
    if not runs or any(run["inputHashes"] != runs[0]["inputHashes"] for run in runs):
        raise ValueError("Compared processes must use the same fixture bytes")
    profiles = {}
    for profile in ("torch", "onnx"):
        selected = [run for run in runs if run["profile"] == profile]
        samples = [sample for run in selected for sample in run["samples"]]
        profiles[profile] = {
            "scans": len(samples),
            "timings": {
                key: statistics.median(sample[key] for sample in samples)
                for key in ("scanMs", "detectMs", "recognizeMs", "tokenizeMs")
            },
            "perFixture": {
                name: statistics.median(
                    sample["scanMs"] for sample in samples if sample["fixture"] == name
                )
                for name in selected[0]["outputs"]
            },
            "peakRssBytes": [run["peakRssBytes"] for run in selected],
            "setupMs": [run["processSetupMs"] for run in selected],
            "pipelineText": selected[0]["pipelineText"],
            "recognition": selected[0]["recognition"],
            "geometry": {
                stage: {
                    key: sum(case[stage][key] for case in selected[0]["geometry"])
                    for key in (
                        "truePositive",
                        "falsePositive",
                        "falseNegative",
                        "correctOrientation",
                    )
                }
                for stage in ("firstPass", "finalRegions")
            },
            "repeatable": all(
                run["outputs"] == selected[0]["outputs"] for run in selected
            ),
        }
    baseline = next(run for run in runs if run["profile"] == "torch")["outputs"]
    candidate = next(run for run in runs if run["profile"] == "onnx")["outputs"]
    differences = {
        name: {"torch": baseline[name], "onnx": candidate[name]}
        for name in baseline
        if baseline[name] != candidate[name]
    }
    return {
        "profiles": profiles,
        "changedFixtures": differences,
        "sameFullOutputs": not differences,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "services/ocr/build/lindera-experiment-20261017/scan-benchmark",
    )
    parser.add_argument(
        "--exports",
        type=Path,
        default=ROOT / "services/ocr/build/resource-reduction-20261018/onnx-export",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "services/ocr/build/macos-onnx-investigation-20261018",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--profile", choices=("torch", "onnx"))
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin" or args.repeats < 1 or args.rounds < 1:
        parser.error(
            "This investigation requires macOS and positive repeat/round counts"
        )
    if args.profile:
        if args.result is None:
            parser.error("Worker profile requires --result")
        worker(args)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    runs = []
    for round_index in range(args.rounds):
        order = ("torch", "onnx") if round_index % 2 == 0 else ("onnx", "torch")
        for profile in order:
            result = args.output / f"{round_index}-{profile}.json"
            env = configure(ROOT, dict(os.environ))
            interpreter = ROOT / (
                "services/ocr/build/release-venv/bin/python"
                if profile == "torch"
                else "services/ocr/build/onnx-prototype/venv/bin/python"
            )
            if profile == "onnx":
                env["PYTHONPATH"] += (
                    os.pathsep
                    + str(ROOT / "scripts")
                    + os.pathsep
                    + str(
                        ROOT
                        / "services/ocr/build/resource-reduction-20261018/torch-free-site"
                    )
                )
                env["USE_TORCH"] = "0"
            subprocess.run(
                [
                    "rtk",
                    "proxy",
                    str(interpreter),
                    str(Path(__file__).resolve()),
                    "--profile",
                    profile,
                    "--fixtures",
                    str(args.fixtures.resolve()),
                    "--exports",
                    str(args.exports.resolve()),
                    "--repeats",
                    str(args.repeats),
                    "--result",
                    str(result),
                ],
                env=env,
                cwd=ROOT,
                check=True,
            )
            runs.append(json.loads(result.read_text()))
    report = {
        "sourceCommit": subprocess.check_output(
            ["rtk", "proxy", "git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "benchmarkSha256": digest(Path(__file__)),
        "exportManifestSha256": digest(args.exports / "export.json"),
        "rounds": args.rounds,
        "repeats": args.repeats,
        "scope": "macOS CPU source processes; synthetic fixtures; no installer or production backend changes",
        "summary": summarize(runs),
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
