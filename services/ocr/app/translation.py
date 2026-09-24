"""On-demand, offline Japanese-to-English translation and local result cache."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Protocol

from app.models import TranslationResponse


class TranslationProvider(Protocol):
    @property
    def identity(self) -> str: ...

    def translate(self, text: str) -> str: ...


class LocalMarianProvider:
    """Load a user-installed Marian ja-en model without network downloads."""

    @property
    def model_path(self) -> Path:
        configured = environ.get("YOMIMADO_TRANSLATION_MODEL")
        if not configured:
            raise FileNotFoundError(
                "Set YOMIMADO_TRANSLATION_MODEL to a local Japanese-to-English model directory"
            )
        path = Path(configured).expanduser()
        if not path.is_dir():
            raise FileNotFoundError(f"Translation model directory does not exist: {path}")
        return path

    @property
    def identity(self) -> str:
        return f"local-marian:{self.model_path.resolve()}"

    def translate(self, text: str) -> str:
        tokenizer, model = _load_model(self.model_path.resolve())
        inputs = tokenizer(text, return_tensors="pt")
        if inputs["input_ids"].shape[-1] > 512:
            raise ValueError("Selected text is too long for the local translation model")
        output = model.generate(**inputs, max_new_tokens=256)
        translation = tokenizer.decode(output[0], skip_special_tokens=True).strip()
        if not translation:
            raise RuntimeError("The local translation model returned no text")
        return translation


@lru_cache(maxsize=1)
def _load_model(model_path: Path):
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as error:
        raise ImportError("Install yomimado-ocr[translation] to use local translation") from error
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path), local_files_only=True)
    model.eval()
    return tokenizer, model


def default_cache_path() -> Path:
    configured = environ.get("YOMIMADO_TRANSLATION_CACHE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "yomimado" / "translation.sqlite3"


class TranslationService:
    def __init__(self, provider: TranslationProvider, cache_path: Path):
        self.provider = provider
        self.cache_path = cache_path

    def translate(self, text: str) -> TranslationResponse:
        source = text.strip()
        if not source:
            raise ValueError("Select or enter Japanese text before translating")
        provider_id = self.provider.identity
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.cache_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS translations (
                    provider TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    PRIMARY KEY (provider, source_text)
                )"""
            )
            row = connection.execute(
                "SELECT translated_text FROM translations WHERE provider = ? AND source_text = ?",
                (provider_id, source),
            ).fetchone()
            if row is not None:
                return TranslationResponse(
                    sourceText=source, translatedText=row[0], provider=provider_id, cached=True
                )
        translated = self.provider.translate(source)
        with sqlite3.connect(self.cache_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO translations VALUES (?, ?, ?)",
                (provider_id, source, translated),
            )
        return TranslationResponse(
            sourceText=source, translatedText=translated, provider=provider_id, cached=False
        )
