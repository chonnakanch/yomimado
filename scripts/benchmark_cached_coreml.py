"""Isolated macOS cache/CoreML investigation with bounded child processes.

Reuses the existing full OCR benchmark and its geometry/text scoring. Never
starts, changes or stops an application service. All inputs are local.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from benchmark_macos_onnx import ROOT, digest, worker
from dev_lindera_service import configure

PROFILES = (
    "torch",
    "cpu-full",
    "cpu-cached",
    "coreml-encoder",
    "coreml-cached",
    "coreml-all",
)


def candidate(args, profile=False):
    from onnx_cached_experiment import recognizer

    model = ROOT / "apps/desktop/src-tauri/resources/ocr/assets/manga-ocr-base"
    return recognizer(
        model,
        args.exports,
        args.cached
        if "cached" in args.variant or args.variant == "coreml-all"
        else None,
        args.output / "coreml-cache",
        coreml_encoder=args.variant.startswith("coreml"),
        coreml_decoder=args.variant == "coreml-all",
        profile=profile,
    )


def verify(args):
    from windows_onnx_backend import verified_exports

    verified_exports(args.exports, "ocr")
    manifest = json.loads((args.cached / "export.json").read_text())
    for name, item in manifest["outputs"].items():
        if Path(name).name != name or digest(args.cached / name) != item["sha256"]:
            raise ValueError("Cached export differs: " + name)


def diagnostic(args):
    import resource
    import time

    import numpy as np
    from onnx_cached_experiment import CachedStep, profile_summary, session
    from PIL import Image

    verify(args)
    started = time.perf_counter()
    model = candidate(args, profile=True)
    reference = json.loads((args.fixtures / "comparison.json").read_text())
    cases = []
    for fixture in reference["geometryAccuracy"]:
        image = Image.open(args.fixtures / (fixture["fixture"] + ".png"))
        for case in fixture["expected"]:
            x1, y1, x2, y2 = case["box"]
            crop = image.crop(
                (
                    max(0, x1 - 8),
                    max(0, y1 - 8),
                    min(image.width, x2 + 8),
                    min(image.height, y2 + 8),
                )
            )
            begin = time.perf_counter()
            predicted = model(crop)
            cases.append(
                {
                    "fixture": fixture["fixture"],
                    "expected": case["text"],
                    "predicted": predicted,
                    "tokens": model.last_tokens,
                    "ms": (time.perf_counter() - begin) * 1000,
                }
            )
            print(args.variant + " diagnostic " + fixture["fixture"], flush=True)
    sessions = {"encoder": model.encoder, "decoder": model.decoder}
    if model.prefill:
        sessions["prefill"] = model.prefill
    profiles = {name: profile_summary(value) for name, value in sessions.items()}
    parity = []
    if args.variant == "cpu-cached":
        # Check traced dynamic cache lengths and beam selection independently of
        # final text: exercise duplicate parents and non-identity reordering.
        full, _ = session(
            args.exports / "ocr-decoder.onnx", False, args.output / "parity"
        )
        pixels = model.processor(
            crop.convert("L").convert("RGB"), return_tensors="np"
        ).pixel_values
        hidden = model.encoder.run(None, {"pixel_values": pixels})[0]
        for beams in (1, 4):
            step = CachedStep(model.prefill, model.decoder, hidden)
            ids = np.full((beams, 1), model.policy.start, dtype=np.int64)
            for length in range(1, 25):
                actual = step(ids)
                expected = full.run(
                    None,
                    {
                        "input_ids": ids,
                        "encoder_hidden_states": np.repeat(hidden, beams, axis=0),
                    },
                )[0][:, -1, :]
                np.testing.assert_allclose(actual, expected, atol=2e-4, rtol=1e-4)
                parity.append(
                    {
                        "beams": beams,
                        "length": length,
                        "maxAbsError": float(np.max(np.abs(actual - expected))),
                    }
                )
                parents = np.array([0]) if beams == 1 else np.array([3, 1, 1, 0])
                ids = np.column_stack(
                    (ids[parents], np.argmax(actual[parents], axis=1))
                )
    result = {
        "variant": args.variant,
        "loadMs": model.load_ms,
        "elapsedMs": (time.perf_counter() - started) * 1000,
        "cases": cases,
        "profiles": profiles,
        "logitParity": parity,
        "peakRssBytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def run_worker(args):
    verify(args)
    if args.variant == "torch":
        worker(
            SimpleNamespace(
                profile="torch",
                fixtures=args.fixtures,
                exports=args.exports,
                repeats=args.repeats,
                result=args.result,
            )
        )
        result = json.loads(args.result.read_text())
        result.update(variant=args.variant, experimentSha256=digest(Path(__file__)))
        args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return
    import onnx_runtime

    holder = []

    def factory(*unused):
        value = candidate(args)
        holder.append(value)
        return value

    worker_args = SimpleNamespace(
        profile="torch" if args.variant == "torch" else "onnx",
        fixtures=args.fixtures,
        exports=args.exports,
        repeats=args.repeats,
        result=args.result,
    )
    with patch.object(onnx_runtime, "OnnxRecognizer", factory):
        worker(worker_args)
    result = json.loads(args.result.read_text())
    result["variant"] = args.variant
    result["experimentSha256"] = digest(Path(__file__))
    if holder:
        result["sessionLoadMs"] = holder[0].load_ms
    args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


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
        default=ROOT / "services/ocr/build/macos-onnx-cached-coreml-20261018",
    )
    parser.add_argument("--cached", type=Path)
    parser.add_argument("--variant", choices=PROFILES)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=PROFILES,
        default=["torch", "cpu-full", "cpu-cached", "coreml-cached"],
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()
    if sys.platform != "darwin" or args.repeats < 1 or args.rounds < 1:
        parser.error("Requires macOS and positive repeats/rounds")
    args.output.mkdir(parents=True, exist_ok=True)
    args.cached = args.cached or args.output / "cached-export"
    if args.variant:
        if not args.result:
            parser.error("Worker requires --result")
        if args.diagnostic:
            diagnostic(args)
        else:
            run_worker(args)
        return
    runs = []
    for round_index in range(args.rounds):
        order = args.profiles if round_index % 2 == 0 else list(reversed(args.profiles))
        for variant in order:
            result = args.output / f"{round_index}-{variant}.json"
            env = configure(ROOT, dict(os.environ))
            env["PYTHONPATH"] += os.pathsep + str(ROOT / "scripts")
            interpreter = ROOT / "services/ocr/build/release-venv/bin/python"
            if variant != "torch":
                interpreter = ROOT / "services/ocr/build/onnx-prototype/venv/bin/python"
                env["PYTHONPATH"] += os.pathsep + str(
                    ROOT
                    / "services/ocr/build/resource-reduction-20261018/torch-free-site"
                )
                env["USE_TORCH"] = "0"
            command = [
                "rtk",
                "proxy",
                str(interpreter),
                str(Path(__file__).resolve()),
                "--variant",
                variant,
                "--result",
                str(result),
                "--fixtures",
                str(args.fixtures),
                "--exports",
                str(args.exports),
                "--cached",
                str(args.cached),
                "--output",
                str(args.output),
                "--repeats",
                str(args.repeats),
            ]
            subprocess.run(command, env=env, cwd=ROOT, check=True, timeout=600)
            runs.append(json.loads(result.read_text()))
    baseline = runs[0]
    if any(run["inputHashes"] != baseline["inputHashes"] for run in runs):
        raise ValueError("Fixture bytes changed between workers")
    summaries = {}
    for variant in args.profiles:
        selected = [run for run in runs if run["variant"] == variant]
        samples = [item for run in selected for item in run["samples"]]
        summaries[variant] = {
            "scans": len(samples),
            "medianMs": {
                key: statistics.median(item[key] for item in samples)
                for key in ("scanMs", "detectMs", "recognizeMs")
            },
            "blocks": [
                {
                    key: statistics.median(item[key] for item in run["samples"])
                    for key in ("scanMs", "detectMs", "recognizeMs")
                }
                for run in selected
            ],
            "sameFullOutputs": all(
                run["outputs"] == baseline["outputs"] for run in selected
            ),
            "pipelineText": selected[0]["pipelineText"],
            "recognition": selected[0]["recognition"],
            "peakRssBytes": [run["peakRssBytes"] for run in selected],
            "setupMs": [run["processSetupMs"] for run in selected],
        }
    report = {
        "profiles": summaries,
        "sourceScripts": {
            name: digest(ROOT / "scripts" / name)
            for name in (
                "benchmark_cached_coreml.py",
                "onnx_cached_experiment.py",
                "benchmark_macos_onnx.py",
            )
        },
        "cachedExportSha256": digest(args.cached / "export.json"),
        "rounds": args.rounds,
        "repeats": args.repeats,
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
