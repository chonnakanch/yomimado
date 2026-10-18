from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tokenizer import lindera, provider
from app.tokenizer.sudachi import SudachiTokenizer


def native(surface, start, end, details=None, unknown=False):
    return {
        "surface": surface,
        "byte_start": start,
        "byte_end": end,
        "is_unknown": unknown,
        "details": details
        if details is not None
        else ["名詞", "一般", "*", "*", "*", "*", surface, "ガッコウ", "ガッコー"],
    }


def backend(monkeypatch, raw):
    monkeypatch.setenv("YOMIMADO_LINDERA_DICTIONARY", "/local/experimental-ipadic")
    tokens = [SimpleNamespace(to_dict=lambda value=value: value) for value in raw]
    engine = SimpleNamespace(tokenize=lambda text: tokens)
    monkeypatch.setattr(lindera, "_backend", lambda path: (engine, Lock()))
    return lindera.LinderaTokenizer()


def test_maps_utf8_bytes_to_original_codepoint_spans_and_preserves_inflection(monkeypatch):
    text = "🙂学校で食べた。"
    tokenizer = backend(
        monkeypatch,
        [
            native("🙂", 0, 4, ["記号"], True),
            native("学校", 4, 10),
            native("で", 10, 13),
            native(
                "食べ",
                13,
                19,
                ["動詞", "自立", "*", "*", "一段", "連用形", "食べる", "タベ", "タベ"],
            ),
            native("た", 19, 22),
            native("。", 22, 25, ["記号"], True),
        ],
    )
    tokens = tokenizer.tokenize(text)
    assert [x.surface for x in tokens] == ["学校", "で", "食べ", "た"]
    assert all(text[x.start : x.end] == x.surface for x in tokens)
    assert (tokens[0].start, tokens[0].end, tokens[0].reading) == (1, 3, "ガッコウ")
    assert (tokens[2].dictionaryForm, tokens[2].reading) == ("食べる", "タベ")
    assert tokens[2].partOfSpeech == "動詞 / 自立 / 一段 / 連用形"


@pytest.mark.parametrize("missing", ["*", ""])
def test_unknown_tokens_preserve_surface_when_reading_and_base_are_unavailable(
    monkeypatch, missing
):
    tokenizer = backend(
        monkeypatch,
        [
            native(
                "ABC", 0, 3, ["名詞", "一般", "*", "*", "*", "*", missing, missing, missing], True
            )
        ],
    )
    token = tokenizer.tokenize("ABC")[0]
    assert (token.surface, token.reading, token.dictionaryForm) == ("ABC", "ABC", "ABC")


@pytest.mark.parametrize(
    "raw",
    [
        [native("学", 1, 3)],  # Inside a UTF-8 character.
        [native("学", 0, 6)],  # The declared surface does not cover the span.
        [native("学校", 0, 6), native("校", 3, 6)],  # Overlapping output.
        [native("学校", 0, 6, ["名詞"])],  # Known word with incompatible features.
        [native("学校", 0, 6, [None] * 9)],
    ],
)
def test_rejects_incompatible_native_output(monkeypatch, raw):
    with pytest.raises(RuntimeError, match="features or text offsets"):
        backend(monkeypatch, raw).tokenize("学校")


def test_resolves_development_dictionary_without_environment_override(monkeypatch):
    monkeypatch.delenv("YOMIMADO_LINDERA_DICTIONARY", raising=False)
    assert (
        lindera.dictionary_path()
        == Path(lindera.__file__).resolve().parents[2] / "local-dictionaries/lindera-ipadic"
    )


def test_resolves_frozen_dictionary_relative_to_executable(monkeypatch, tmp_path):
    monkeypatch.delenv("YOMIMADO_LINDERA_DICTIONARY", raising=False)
    monkeypatch.setattr(lindera.sys, "frozen", True, raising=False)
    monkeypatch.setattr(lindera.sys, "executable", str(tmp_path / "runtime/yomimado-ocr"))
    assert lindera.dictionary_path() == tmp_path / "assets/lindera-ipadic"


def test_verifies_pinned_dictionary_bytes_and_membership(tmp_path: Path):
    source = tmp_path / "dict.words"
    source.write_bytes(b"pinned input")
    pins = {source.name: hashlib.sha256(source.read_bytes()).hexdigest()}
    lindera.verify_dictionary(tmp_path, pins)
    source.write_bytes(b"changed input")
    with pytest.raises(RuntimeError, match="checksum"):
        lindera.verify_dictionary(tmp_path, pins)
    source.unlink()
    with pytest.raises(RuntimeError, match="file set"):
        lindera.verify_dictionary(tmp_path, pins)


def test_default_is_lindera_in_source_and_frozen_apps(monkeypatch):
    monkeypatch.delenv("YOMIMADO_TOKENIZER", raising=False)
    assert isinstance(provider.get_tokenizer(), lindera.LinderaTokenizer)
    monkeypatch.setattr(provider.sys, "frozen", True, raising=False)
    assert isinstance(provider.get_tokenizer(), lindera.LinderaTokenizer)
    monkeypatch.setenv("YOMIMADO_TOKENIZER", "sudachi")
    with pytest.raises(RuntimeError, match="development comparisons"):
        provider.get_tokenizer()
    monkeypatch.setattr(provider.sys, "frozen", False)
    assert isinstance(provider.get_tokenizer(), SudachiTokenizer)


def test_api_preserves_contract_with_selected_provider(monkeypatch):
    backend(monkeypatch, [native("学校", 4, 10)])
    monkeypatch.setenv("YOMIMADO_TOKENIZER", "lindera")
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    response = client.post("/api/v1/tokenize", json={"text": "🙂学校"})
    assert response.status_code == 200
    assert response.json()["sourceText"] == "🙂学校"
    assert response.json()["tokens"][0]["start"] == 1


def test_api_reports_missing_dictionary_and_unknown_provider(monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    monkeypatch.setenv("YOMIMADO_TOKENIZER", "lindera")
    monkeypatch.setenv("YOMIMADO_LINDERA_DICTIONARY", "/nonexistent/ipadic")
    assert client.post("/api/v1/tokenize", json={"text": "学校"}).status_code == 503
    monkeypatch.setenv("YOMIMADO_TOKENIZER", "unsupported")
    assert client.post("/api/v1/tokenize", json={"text": "学校"}).status_code == 503
