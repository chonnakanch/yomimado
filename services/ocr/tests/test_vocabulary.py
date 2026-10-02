from pathlib import Path

from fastapi.testclient import TestClient

from app.api import vocabulary as vocabulary_api
from app.main import app
from app.vocabulary import VocabularyStore, default_vocabulary_path


def test_vocabulary_database_uses_app_data_not_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("YOMIMADO_VOCAB_DB", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr("app.vocabulary.sys.platform", "win32")
    assert default_vocabulary_path() == tmp_path / "Roaming" / "YomiMado" / "vocabulary.sqlite3"
    monkeypatch.setenv("YOMIMADO_VOCAB_DB", str(tmp_path / "custom.sqlite3"))
    assert default_vocabulary_path() == tmp_path / "custom.sqlite3"


def test_save_list_update_and_delete_word(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "vocabulary.sqlite3"
    monkeypatch.setattr(vocabulary_api, "store", VocabularyStore(database))
    client = TestClient(app)
    payload = {
        "surface": "今日",
        "reading": "キョウ",
        "dictionaryForm": "今日",
        "meanings": ["today", "this day"],
        "sourceText": "今日はいい日だ。",
    }
    assert client.get("/api/v1/vocabulary").json() == {"words": []}
    saved = client.post("/api/v1/vocabulary", json=payload)
    assert saved.status_code == 200
    word = saved.json()
    assert word["id"] > 0
    assert word["surface"] == "今日"
    assert word["meanings"] == ["today", "this day"]
    assert word["sourceText"] == "今日はいい日だ。"
    assert word["createdAt"]

    revised = client.post("/api/v1/vocabulary", json={**payload, "meanings": ["today"]})
    assert revised.status_code == 200
    assert revised.json()["id"] == word["id"]
    assert revised.json()["createdAt"] == word["createdAt"]
    assert VocabularyStore(database).list()[0].meanings == ["today"]
    assert len(client.get("/api/v1/vocabulary").json()["words"]) == 1

    deleted = client.delete(f"/api/v1/vocabulary/{word['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/vocabulary").json() == {"words": []}
    assert client.delete(f"/api/v1/vocabulary/{word['id']}").status_code == 404


def test_same_word_can_keep_distinct_source_sentences(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vocabulary_api, "store", VocabularyStore(tmp_path / "words.sqlite3"))
    client = TestClient(app)
    base = {
        "surface": "学校",
        "reading": "ガッコウ",
        "dictionaryForm": "学校",
        "meanings": ["school"],
    }
    first = client.post("/api/v1/vocabulary", json={**base, "sourceText": "学校に行く。"})
    second = client.post("/api/v1/vocabulary", json={**base, "sourceText": "学校は休み。"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert len(client.get("/api/v1/vocabulary").json()["words"]) == 2


def test_rejects_blank_words_and_oversized_meanings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vocabulary_api, "store", VocabularyStore(tmp_path / "words.sqlite3"))
    client = TestClient(app)
    payload = {
        "surface": "   ",
        "reading": "",
        "dictionaryForm": "学校",
        "meanings": [],
        "sourceText": "学校に行く。",
    }
    assert client.post("/api/v1/vocabulary", json=payload).status_code == 422
    assert (
        client.post(
            "/api/v1/vocabulary", json={**payload, "surface": "学校", "meanings": ["x" * 2001]}
        ).status_code
        == 422
    )
    assert client.delete("/api/v1/vocabulary/0").status_code == 422


def test_vocabulary_cors_allows_app_origin() -> None:
    client = TestClient(app)
    for method in ("GET", "DELETE"):
        response = client.options(
            "/api/v1/vocabulary",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": method,
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "tauri://localhost"


def test_save_list_update_and_delete_sentence(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "vocabulary.sqlite3"
    monkeypatch.setattr(vocabulary_api, "store", VocabularyStore(database))
    client = TestClient(app)
    assert client.get("/api/v1/sentences").json() == {"sentences": []}

    saved = client.post("/api/v1/sentences", json={"sourceText": "  今日はいい日だ。  "})
    assert saved.status_code == 200
    sentence = saved.json()
    assert sentence["sourceText"] == "今日はいい日だ。"
    assert sentence["translatedText"] is None
    assert sentence["createdAt"]

    revised = client.post(
        "/api/v1/sentences",
        json={"sourceText": "今日はいい日だ。", "translatedText": "It's a good day."},
    )
    assert revised.status_code == 200
    assert revised.json()["id"] == sentence["id"]
    assert revised.json()["createdAt"] == sentence["createdAt"]
    assert revised.json()["translatedText"] == "It's a good day."

    without_translation = client.post("/api/v1/sentences", json={"sourceText": "今日はいい日だ。"})
    assert without_translation.json()["translatedText"] == "It's a good day."
    assert len(client.get("/api/v1/sentences").json()["sentences"]) == 1
    assert len(VocabularyStore(database).list_sentences()) == 1

    assert client.delete(f"/api/v1/sentences/{sentence['id']}").status_code == 204
    assert client.get("/api/v1/sentences").json() == {"sentences": []}
    assert client.delete(f"/api/v1/sentences/{sentence['id']}").status_code == 404


def test_rejects_blank_or_oversized_sentence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(vocabulary_api, "store", VocabularyStore(tmp_path / "words.sqlite3"))
    client = TestClient(app)
    for payload in (
        {"sourceText": "   "},
        {"sourceText": "今日はいい日だ。", "translatedText": "   "},
        {"sourceText": "x" * 2001},
        {"sourceText": "今日はいい日だ。", "translatedText": "x" * 4001},
    ):
        assert client.post("/api/v1/sentences", json=payload).status_code == 422
    assert client.delete("/api/v1/sentences/0").status_code == 422


def test_sentence_cors_allows_app_origin() -> None:
    client = TestClient(app)
    for method in ("GET", "POST", "DELETE"):
        response = client.options(
            "/api/v1/sentences",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": method,
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "tauri://localhost"
