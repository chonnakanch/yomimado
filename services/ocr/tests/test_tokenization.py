import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tokenizer.sudachi import SudachiTokenizer, _offsets

client = TestClient(app)


def test_offsets_accept_original_character_and_utf8_byte_indices() -> None:
    text = "🙂学校。"
    assert _offsets(text, "学校", 1, 3) == (1, 3)
    assert _offsets(text, "学校", 4, 10) == (1, 3)


def test_tokenize_preserves_text_offsets_readings_and_punctuation() -> None:
    pytest.importorskip("sudachipy")
    pytest.importorskip("sudachidict_core")
    text = "今日は学校に行きたくない。🙂"
    tokens = SudachiTokenizer().tokenize(text)

    assert "".join(token.surface for token in tokens) == text
    assert all(text[token.start : token.end] == token.surface for token in tokens)
    assert tokens[0].reading == "キョウ"
    assert next(token for token in tokens if token.surface == "行き").dictionaryForm == "行く"
    assert tokens[-2].surface == "。"
    assert tokens[-1].surface == "🙂"
    assert all(token.partOfSpeech for token in tokens)

    emoji_first = SudachiTokenizer().tokenize("🙂学校")
    assert next(token for token in emoji_first if token.surface == "学校").start == 1


def test_tokenize_endpoint_returns_original_text_and_structured_tokens() -> None:
    pytest.importorskip("sudachipy")
    pytest.importorskip("sudachidict_core")
    text = "学校に行く。"
    response = client.post("/api/v1/tokenize", json={"text": text})

    assert response.status_code == 200
    data = response.json()
    assert data["sourceText"] == text
    assert "".join(token["surface"] for token in data["tokens"]) == text
    assert data["tokens"][0]["reading"] == "ガッコウ"


def test_tokenize_endpoint_rejects_empty_text() -> None:
    response = client.post("/api/v1/tokenize", json={"text": ""})
    assert response.status_code == 422
