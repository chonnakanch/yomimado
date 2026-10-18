"""Windows-only CPU backend assembly; shared macOS service inputs are untouched."""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from os import environ
from pathlib import Path
from sys import platform as HOST_PLATFORM

GRAPH_FILES = {
    "ocr-encoder.onnx",
    "ocr-decoder.onnx",
    "translation-encoder.onnx",
    "translation-decoder.onnx",
    "policies.json",
}


@lru_cache(maxsize=1)
def verified_exports(directory: Path, kind: str | None = None) -> str:
    record = json.loads((directory / "export.json").read_text(encoding="utf-8"))
    outputs = record["outputs"]
    translation_files = {"translation-encoder.onnx", "translation-decoder.onnx", "policies.json"}
    if set(outputs) not in (GRAPH_FILES, translation_files):
        raise ValueError("Unexpected Windows inference graph set")
    if kind == "ocr" and set(outputs) != GRAPH_FILES:
        raise ValueError("Unexpected Windows OCR graph set")
    if kind:
        outputs = {
            name: sha
            for name, sha in outputs.items()
            if name.startswith(kind + "-") or name == "policies.json"
        }
    for name, expected in outputs.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid Windows inference graph checksum")
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Windows inference graph checksum differs: " + name)
    # Stable across install paths; changed graphs/policy cannot reuse old results.
    return hashlib.sha256(json.dumps(outputs, sort_keys=True).encode()).hexdigest()


@lru_cache(maxsize=1)
def cpu_models(repo: Path, detector_model: Path, recognizer_model: Path):
    from onnx_detector import detector_class
    from onnx_runtime import OnnxRecognizer

    exported = recognizer_model.parent / "onnx"
    verified_exports(exported, "ocr")
    return (
        detector_class(repo)(str(detector_model)),
        OnnxRecognizer(recognizer_model, exported),
    )


@lru_cache(maxsize=1)
def translation_provider(model: Path, exported: Path):
    from onnx_runtime import OnnxTranslation

    verified_exports(exported, "translation")
    return OnnxTranslation(model, exported)


class WindowsOnnxTranslator:
    """Lazy local provider: readiness/model setup never performs model inference."""

    @property
    def model_path(self) -> Path:
        from app.translation_resources import local_model_path

        return local_model_path()

    @property
    def identity(self) -> str:
        return "local-onnx-marian:" + verified_exports(
            self.model_path.parent / "onnx", "translation"
        )

    def translate(self, text: str) -> str:
        model = self.model_path
        return translation_provider(model, model.parent / "onnx").translate(text)


def configure_backend() -> None:
    if HOST_PLATFORM != "win32":
        raise RuntimeError("This bundled backend is restricted to Windows")
    environ["USE_TORCH"] = "0"
    environ["HF_HUB_OFFLINE"] = "1"
    environ["TRANSFORMERS_OFFLINE"] = "1"
    import onnxruntime

    onnxruntime.disable_telemetry_events()
    from app.api import translation
    from app.pipeline import real_ocr
    from app.translation import TranslationService, default_cache_path
    from app.translation_preferences import ConfiguredTranslationProvider

    # Assemble the existing Python API boundary in this Windows process only.
    # No shared route, OCR pipeline, coordinate transform or macOS file changes.
    real_ocr._models = cpu_models
    translation.service = TranslationService(ConfiguredTranslationProvider(), default_cache_path())
