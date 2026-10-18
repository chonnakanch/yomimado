"""Persistent translation selection and managed imports of compatible local models."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

from app.translation_resources import digest, download_lock, resources

LOCK = threading.RLock()
MAX_IMPORT_BYTES = 2 * 1024**3
MODEL_FILES = {
    "config.json",
    "tokenizer_config.json",
    "generation_config.json",
    "vocab.json",
    "source.spm",
    "target.spm",
    "special_tokens_map.json",
    "added_tokens.json",
    "README.md",
    "LICENSE",
    "LICENSE.txt",
}
ONNX_FILES = {
    "translation-encoder.onnx",
    "translation-decoder.onnx",
    "policies.json",
    "export.json",
}


def backend() -> str:
    if os.environ.get("USE_TORCH") == "0":
        return "onnx"
    return "torch"


def read_settings() -> dict:
    path = resources().root / "preferences.json"
    if not path.exists():
        return {"provider": "builtin", "ollamaModel": "", "imported": None}
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Translation preferences are invalid")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("provider") not in {
        "builtin",
        "imported",
        "ollama",
    }:
        raise ValueError("Translation preferences are invalid")
    return value


def save_settings(value: dict) -> None:
    root = resources().root
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(value, output)
            output.close()
            os.replace(temporary, root / "preferences.json")
        finally:
            temporary.unlink(missing_ok=True)


def settings_status() -> dict:
    with LOCK:
        value = read_settings()
        imported = value.get("imported")
        return {
            "provider": value["provider"],
            "ollamaModel": value.get("ollamaModel", ""),
            "importedModel": imported["name"] if imported else None,
            "backend": backend(),
        }


def imported_path(value: dict | None = None) -> Path:
    value = value or read_settings()
    record = value.get("imported")
    if not isinstance(record, dict) or not isinstance(record.get("id"), str):
        raise TypeError("Import a compatible local model first")
    from app.translation_resources import SHA

    if not SHA.fullmatch(record["id"]) or record.get("backend") != backend():
        raise ValueError("The imported model is incompatible with this runtime")
    path = resources().root / "custom" / record["id"] / "model"
    if not path.is_dir() or path.is_symlink():
        raise FileNotFoundError("The imported model is missing. Import it again.")
    verify_import(path.parent, record["id"])
    return path


@lru_cache(maxsize=4)
def verify_import(directory: Path, identity: str) -> None:
    pins = json.loads((directory / "import.json").read_text(encoding="utf-8"))
    if hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest() != identity:
        raise ValueError("The imported model record has changed. Import it again.")
    allowed = {"model/" + name for name in MODEL_FILES | {"model.safetensors", "pytorch_model.bin"}}
    allowed |= {"onnx/" + name for name in ONNX_FILES}
    if not isinstance(pins, dict) or not set(pins) <= allowed:
        raise ValueError("The imported model record contains invalid files")
    for name, pin in pins.items():
        path = directory / name
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(directory.resolve())
            or path.stat().st_size != pin["bytes"]
            or digest(path) != pin["sha256"]
        ):
            raise ValueError("The imported model has changed. Import it again.")


def select_provider(provider: str, model: str = "") -> dict:
    from app.ollama_translation import local_model

    if provider not in {"builtin", "imported", "ollama"}:
        raise ValueError("Choose a supported translation provider")
    if provider == "ollama":
        model = local_model(model)["name"]
    with LOCK:
        value = read_settings()
        if provider == "imported":
            imported_path(value)
        value["provider"] = provider
        if provider == "ollama":
            value["ollamaModel"] = model
        save_settings(value)
        return settings_status()


def small_json(path: Path) -> dict:
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Model configuration is too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("auto_map"):
        raise ValueError("Models requiring custom Python code are not supported")
    return value


def collect_files(source: Path) -> dict[str, Path]:
    model = source / "model" if (source / "model/config.json").is_file() else source
    config = small_json(model / "config.json")
    tokenizer = small_json(model / "tokenizer_config.json")
    if (
        config.get("model_type") != "marian"
        or tokenizer.get("tokenizer_class", "MarianTokenizer") != "MarianTokenizer"
    ):
        raise ValueError(
            "Import a Japanese-to-English Marian model folder. Use Ollama for other model families."
        )
    if tokenizer.get("source_lang", "ja") != "ja" or tokenizer.get("target_lang", "en") != "en":
        raise ValueError("Choose a Japanese-to-English model")
    required = {"config.json", "tokenizer_config.json", "vocab.json", "source.spm", "target.spm"}
    files = {"model/" + name: model / name for name in MODEL_FILES if (model / name).exists()}
    if not required <= {path.name for path in files.values()}:
        raise ValueError("The model folder is missing tokenizer files")
    if backend() == "torch":
        weight = next(
            (
                model / name
                for name in ("model.safetensors", "pytorch_model.bin")
                if (model / name).is_file()
            ),
            None,
        )
        if not weight:
            raise ValueError("The model folder needs model.safetensors or pytorch_model.bin")
        files["model/" + weight.name] = weight
    else:
        exported = model.parent / "onnx"
        files.update({"onnx/" + name: exported / name for name in ONNX_FILES})
        policy = small_json(exported / "policies.json").get("translation", {})
        if (
            not isinstance(policy, dict)
            or not 1 <= policy.get("beams", 0) <= 8
            or not 2 <= policy.get("limit", 0) <= 512
        ):
            raise ValueError("The ONNX model needs a compatible translation generation policy")
    size = 0
    for path in files.values():
        if (
            not path.is_file()
            or not path.resolve().is_relative_to(source)
            or path.stat().st_size == 0
        ):
            raise ValueError("The model folder contains missing or unsafe files")
        size += path.stat().st_size
    if size > MAX_IMPORT_BYTES:
        raise ValueError("The imported model exceeds the 2 GiB limit")
    return files


def validate_model(model: Path) -> None:
    if backend() == "onnx":
        from windows_onnx_backend import translation_provider

        translation_provider(model, model.parent / "onnx")
    else:
        from app.translation import _load_model

        _load_model(model)


def import_model(folder: str) -> dict:
    source = Path(folder).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("Choose an existing model folder")
    root = resources().root
    root.mkdir(parents=True, exist_ok=True)
    # Use the same cross-process lock as built-in downloads, so neither can
    # clean up or replace files belonging to an active installation.
    with LOCK, download_lock(root):
        files = collect_files(source)
        with tempfile.TemporaryDirectory(prefix=".import-", dir=root) as temporary:
            staged = Path(temporary) / "staged"
            pins = {}
            for name, path in files.items():
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                pins[name] = {"sha256": digest(target), "bytes": target.stat().st_size}
            identity = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()
            # Validate the managed copy before changing the user's selection.
            validate_model(staged / "model")
            (staged / "import.json").write_text(json.dumps(pins), encoding="utf-8")
            destination = root / "custom" / identity
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                if any(
                    not (destination / name).is_file()
                    or digest(destination / name) != pin["sha256"]
                    for name, pin in pins.items()
                ):
                    raise ValueError(
                        "An existing imported model is damaged. Choose another model folder."
                    )
            else:
                staged.rename(destination)
            verify_import.cache_clear()
            verify_import(destination, identity)
            value = read_settings()
            value.update(
                provider="imported",
                imported={"id": identity, "name": source.name, "backend": backend()},
            )
            save_settings(value)
    return settings_status()


class ConfiguredTranslationProvider:
    """Resolve once per request so selection changes cannot mix model/cache IDs."""

    def __init__(self, builtin):
        self.builtin = builtin

    def snapshot(self):
        from app.ollama_translation import OllamaProvider

        with LOCK:
            value = read_settings()
            if value["provider"] == "ollama":
                return OllamaProvider(value["ollamaModel"])
            if value["provider"] == "imported":
                path = imported_path(value)
                return ImportedProvider(path, value["imported"]["id"])
            return self.builtin


class ImportedProvider:
    def __init__(self, path: Path, identity: str):
        self.path = path
        self.identity = "imported-marian:" + identity

    def translate(self, text: str) -> str:
        if backend() == "onnx":
            from windows_onnx_backend import translation_provider

            return translation_provider(self.path, self.path.parent / "onnx").translate(text)
        from app.translation import translate_with_model

        return translate_with_model(self.path, text)
