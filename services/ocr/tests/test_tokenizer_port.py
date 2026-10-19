"""The HTTP/learning contract must work without importing a native adapter."""

import pytest
from fastapi.testclient import TestClient

from app.api.tokenization import resolve_tokenizer
from app.main import app
from app.models import TextToken


class FakeTokenizer:
    def tokenize(self, text: str) -> list[TextToken]:
        assert text == "🙂学校。"
        return [
            TextToken(
                surface="学校",
                reading="ガッコウ",
                dictionaryForm="学校",
                start=1,
                end=3,
                partOfSpeech="名詞",
            )
        ]


class UnavailableTokenizer:
    def tokenize(self, text: str) -> list[TextToken]:
        raise RuntimeError("Selected engine's resource is unavailable")


@pytest.fixture
def client():
    previous = app.dependency_overrides.copy()
    try:
        with TestClient(
            app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_an_independent_adapter_preserves_the_public_contract(client, monkeypatch):
    # An invalid provider proves the route uses the injected port, not a native
    # engine or the provider factory behind its caller's back.
    monkeypatch.setenv("YOMIMADO_TOKENIZER", "not-installed")
    app.dependency_overrides[resolve_tokenizer] = FakeTokenizer
    response = client.post("/api/v1/tokenize", json={"text": "🙂学校。"})
    assert response.status_code == 200
    assert response.json() == {
        "sourceText": "🙂学校。",
        "tokens": [
            {
                "surface": "学校",
                "reading": "ガッコウ",
                "dictionaryForm": "学校",
                "start": 1,
                "end": 3,
                "partOfSpeech": "名詞",
            }
        ],
    }


def test_an_unavailable_adapter_returns_an_explicit_setup_error(client):
    app.dependency_overrides[resolve_tokenizer] = UnavailableTokenizer
    response = client.post("/api/v1/tokenize", json={"text": "学校"})
    assert response.status_code == 503
    assert "resource is unavailable" in response.json()["detail"]
