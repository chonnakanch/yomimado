"""Compare offline CPU ONNX and existing Torch backends in separate processes.

Textual reports only; no model weights/screenshots are published. Exit nonzero on
any tested text/geometry difference. This is not installed-app or licence approval.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXTS = ("今日は学校に行きます。", "この本は面白いです。", "無理のしすぎはダメだよ。")


def reject_torch(event, arguments):
    # Audit actual imports, not importlib's harmless package-availability probes.
    if event == "import" and arguments[0].split(".")[0] in {
        "torch",
        "torchvision",
        "manga_ocr",
    }:
        raise ImportError("The ONNX child must not import " + arguments[0])


def failure_annotation(message: str) -> None:
    # Only the fixed synthetic probe's text/logs reach this helper. No credentials
    # or private fixture inputs are used by the read-only prototype workflow.
    print(message, file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::error title=Windows ONNX comparison failed::" + escaped, flush=True)


def worker(args) -> dict:
    if args.worker == "onnx":
        os.environ["USE_TORCH"] = "0"
        sys.addaudithook(reject_torch)
    from app.pipeline import real_ocr
    from app.translation import LocalMarianProvider, TranslationService

    if args.worker == "onnx":
        from onnx_detector_probe import detector_class
        from onnx_runtime_probe import OnnxRecognizer, OnnxTranslation

        detector = detector_class(args.detector_repo)(str(args.detector_model))
        recognizer = OnnxRecognizer(args.ocr_model, args.exported)
        real_ocr._models = lambda *unused: (detector, recognizer)
        provider = OnnxTranslation(args.translation_model, args.exported)
    else:
        import torch

        torch.set_num_threads(2)
        provider = LocalMarianProvider()
    report = {"backend": args.worker, "ocr": {}, "translation": {}, "timings": {}}
    for orientation in ("horizontal", "vertical"):
        start = time.monotonic()
        image = ROOT / f"scripts/fixtures/windows-ocr-{orientation}.png"
        result = real_ocr.recognize_with_models(image.read_bytes()).model_dump()
        if not any(
            "学校" in region["text"] and region["orientation"] == orientation
            for region in result["regions"]
        ):
            raise RuntimeError(
                "Synthetic OCR fixture did not produce its expected text/geometry"
            )
        report["ocr"][orientation] = result
        report["timings"]["ocr-" + orientation] = time.monotonic() - start
    database = args.cache
    service = TranslationService(provider, database)
    for text in TEXTS:
        start = time.monotonic()
        translated = service.translate(text)
        if translated.cached or not translated.translatedText:
            raise RuntimeError("Uncached translation probe failed")
        report["translation"][text] = translated.translatedText
        report["timings"][text] = time.monotonic() - start
    restarted = TranslationService(provider, database)
    if not restarted.translate(TEXTS[0]).cached:
        raise RuntimeError("Translation cache did not survive service recreation")
    report["cacheSurvivedNewService"] = True
    report["torchImported"] = any(
        name.split(".")[0] in {"torch", "torchvision"} for name in sys.modules
    )
    if args.worker == "onnx" and report["torchImported"]:
        raise RuntimeError("Torch leaked into the ONNX worker")
    report["platform"] = {
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    report["versions"] = {
        name: importlib.metadata.version(name)
        for name in ("numpy", "transformers", "Pillow")
    }
    if args.worker == "onnx":
        import onnxruntime

        report["versions"]["onnxruntime"] = onnxruntime.__version__
        report["runtimeBuild"] = onnxruntime.get_build_info()
        if sys.platform == "win32":
            # Record actual modules after inference, without treating prototype
            # paths as proof of a self-contained installed runtime.
            script = (
                f"@(Get-Process -Id {os.getpid()}).Modules | ForEach-Object {{ "
                "@{path=$_.FileName; name=$_.ModuleName; sha256=(Get-FileHash $_.FileName -Algorithm SHA256).Hash.ToLower()} "
                "} | ConvertTo-Json -Compress"
            )
            raw = subprocess.check_output(
                ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True,
                encoding="utf-8",
            )
            report["loadedModules"] = json.loads(raw)
            names = [item["name"].lower() for item in report["loadedModules"]]
            if not any(name.startswith("onnxruntime_pybind11_state") for name in names):
                raise RuntimeError("ONNX native inference module was not observed")
            if any(
                name.startswith(("torch", "cudnn", "cublas", "mkl")) for name in names
            ):
                raise RuntimeError("Unexpected Torch/CUDA/MKL native module loaded")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "ocr-model",
        "translation-model",
        "detector-repo",
        "detector-model",
        "exported",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--worker", choices=("baseline", "onnx"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--onnx-python", type=Path)
    parser.add_argument("--onnx-pythonpath")
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            # Resolving a venv interpreter symlink selects its base Python and
            # loses the isolated environment on Unix hosts.
            absolute = value.absolute() if name == "onnx_python" else value.resolve()
            setattr(args, name, absolute)
    # Validate every graph/policy against conversion provenance before inference.
    record = json.loads((args.exported / "export.json").read_text())
    if set(record["outputs"]) != {
        "ocr-encoder.onnx",
        "ocr-decoder.onnx",
        "translation-encoder.onnx",
        "translation-decoder.onnx",
        "policies.json",
    }:
        raise ValueError("Unexpected exported graph/policy set")
    for asset in json.loads((ROOT / "services/ocr/windows-assets.json").read_text()):
        prefix, _, name = asset["path"].partition("/")
        directory = {
            "manga-ocr-base": args.ocr_model,
            "opus-mt-ja-en": args.translation_model,
        }.get(prefix)
        if directory is None:
            continue
        with (directory / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if (
            actual != asset["sha256"]
            or record["sourceInputs"].get(asset["path"]) != actual
        ):
            raise ValueError("Model/tokenizer source input differs: " + asset["path"])
    with args.detector_model.open("rb") as stream:
        if (
            hashlib.file_digest(stream, "sha256").hexdigest()
            != "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f"
        ):
            raise ValueError("Smoke detector is not the pinned user-installed input")
    for name, expected in record["outputs"].items():
        path = args.exported / name
        if path.parent != args.exported:
            raise ValueError("Invalid export path")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("Export hash differs: " + name)
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "CUDA_VISIBLE_DEVICES": "",
            "YOMIMADO_DETECTOR_REPO": str(args.detector_repo),
            "YOMIMADO_DETECTOR_MODEL": str(args.detector_model),
            "YOMIMADO_MANGA_OCR_MODEL": str(args.ocr_model),
            "YOMIMADO_TRANSLATION_MODEL": str(args.translation_model),
        }
    )
    if args.worker:
        if args.cache is None:
            parser.error("--cache is required for a worker")
        result = worker(args)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return
    args.output.mkdir(parents=True, exist_ok=True)
    results = {}
    for backend in ("baseline", "onnx"):
        output = args.output / (backend + ".json")
        interpreter = (
            args.onnx_python
            if backend == "onnx" and args.onnx_python
            else sys.executable
        )
        command = [str(interpreter), str(Path(__file__).resolve()), "--worker", backend]
        for name in (
            "ocr_model",
            "translation_model",
            "detector_repo",
            "detector_model",
            "exported",
        ):
            command.extend(["--" + name.replace("_", "-"), str(getattr(args, name))])
        command.extend(["--output", str(output)])
        print("Testing offline " + backend, flush=True)
        env = dict(os.environ)
        if backend == "onnx" and args.onnx_pythonpath:
            env["PYTHONPATH"] = args.onnx_pythonpath
        # The parent owns cleanup: SQLite connections can remain alive until
        # interpreter shutdown. Windows cannot unlink that open cache file.
        # Both service instances still use the same fresh cache inside the child.
        with tempfile.TemporaryDirectory(prefix="yomimado-onnx-cache-") as temporary:
            command.extend(["--cache", str(Path(temporary) / "translation.sqlite3")])
            with (args.output / (backend + ".log")).open("w") as log:
                try:
                    subprocess.run(
                        command,
                        check=True,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=900,
                        env=env,
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    log.flush()
                    failure_annotation(
                        backend
                        + " worker failed:\n"
                        + (args.output / (backend + ".log")).read_text(
                            encoding="utf-8", errors="replace"
                        )[-6000:]
                    )
                    raise
        results[backend] = json.loads(output.read_text())
    report = {
        "exactOcrParity": results["baseline"]["ocr"] == results["onnx"]["ocr"],
        "exactTranslationParity": results["baseline"]["translation"]
        == results["onnx"]["translation"],
        "torchAbsentFromOnnxWorker": not results["onnx"]["torchImported"],
        "results": results,
        "publicDistributionApproved": False,
        "installedAppVerified": False,
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    if not all(
        report[key]
        for key in (
            "exactOcrParity",
            "exactTranslationParity",
            "torchAbsentFromOnnxWorker",
        )
    ):
        failure_annotation(
            json.dumps(
                {
                    "ocr": {
                        backend: report["results"][backend]["ocr"]
                        for backend in results
                    },
                    "translation": {
                        backend: report["results"][backend]["translation"]
                        for backend in results
                    },
                },
                ensure_ascii=False,
            )
        )
        raise RuntimeError("ONNX parity gate failed; inspect comparison.json")
    print(
        "PASS: tested offline OCR/geometry and uncached translation parity; Torch absent from ONNX child"
    )


if __name__ == "__main__":
    main()
