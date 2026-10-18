import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import translation as translation_api
from app.main import app
from app.translation import LocalMarianProvider, TranslationService


class FakeProvider:
    identity = "test-local-model"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        return "I will go to school."


def test_translation_is_explicit_and_cached(tmp_path: Path, monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(
        translation_api,
        "service",
        TranslationService(provider, tmp_path / "translations.sqlite3"),
    )
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    assert provider.calls == []

    first = client.post("/api/v1/translate", json={"text": " 学校に行く。 "})
    assert first.status_code == 200
    assert first.json() == {
        "sourceText": "学校に行く。",
        "translatedText": "I will go to school.",
        "provider": "test-local-model",
        "cached": False,
    }
    second = client.post("/api/v1/translate", json={"text": "学校に行く。"})
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert provider.calls == ["学校に行く。"]


def test_translation_rejects_blank_text() -> None:
    response = TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ).post("/api/v1/translate", json={"text": "  "})
    assert response.status_code == 422


def test_translation_reports_missing_local_model(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("YOMIMADO_TRANSLATION_MODEL", raising=False)
    monkeypatch.setattr(
        translation_api,
        "service",
        TranslationService(LocalMarianProvider(), tmp_path / "cache.sqlite3"),
    )
    response = TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ).post("/api/v1/translate", json={"text": "学校"})
    assert response.status_code == 503
    assert "YOMIMADO_TRANSLATION_MODEL" in response.json()["detail"]


def test_translation_reports_corrupt_cache_as_service_error(monkeypatch, tmp_path: Path) -> None:
    cache = tmp_path / "cache.sqlite3"
    cache.write_bytes(b"not a SQLite database")
    provider = FakeProvider()
    monkeypatch.setattr(translation_api, "service", TranslationService(provider, cache))

    response = TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ).post("/api/v1/translate", json={"text": "学校"})

    assert response.status_code == 503
    assert "database" in response.json()["detail"]
    assert provider.calls == []


@pytest.mark.parametrize("corrupt_cache", [False, True])
def test_translation_closes_cache_connections(monkeypatch, tmp_path: Path, corrupt_cache) -> None:
    connections = []

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def close(self):
            super().close()
            self.closed = True

    connect = sqlite3.connect

    def tracked_connect(path):
        connection = connect(path, factory=TrackedConnection)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    cache = tmp_path / "cache.sqlite3"
    provider = FakeProvider()
    service = TranslationService(provider, cache)
    if corrupt_cache:
        cache.write_bytes(b"not a SQLite database")
        with pytest.raises(sqlite3.DatabaseError):
            service.translate("学校")
        assert len(connections) == 1
    else:
        assert service.translate("学校").cached is False
        assert len(connections) == 2
        assert all(connection.closed for connection in connections)
        assert service.translate("学校").cached is True
        assert len(connections) == 3
        assert provider.calls == ["学校"]
    assert all(connection.closed for connection in connections)


@pytest.mark.parametrize("origin", ["tauri://localhost", "http://tauri.localhost"])
def test_translation_cors_allows_app_but_not_other_sites(origin: str) -> None:
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    allowed = client.options(
        "/api/v1/translate",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == origin

    denied = client.options(
        "/api/v1/translate",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"},
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
