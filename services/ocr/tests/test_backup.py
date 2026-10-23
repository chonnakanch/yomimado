import copy
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import vocabulary as api
from app.backup import MAX_BACKUP_BYTES, parse_backup
from app.main import app
from app.models import SaveSentenceRequest, SaveWordRequest
from app.vocabulary import VocabularyStore


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "store", VocabularyStore(tmp_path / "saved.sqlite3"))
    with TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ) as client:
        yield client


def sample():
    return {
        "format": "yomimado-saved",
        "version": 1,
        "createdAt": "2026-10-23T12:00:00+00:00",
        "words": [
            {
                "surface": "𠮷野",
                "reading": "ヨシノ",
                "dictionaryForm": "𠮷野",
                "meanings": ["a name", "second meaning"],
                "sourceText": "𠮷野に行く。\n明日だ。",
                "createdAt": "2026-09-01T08:02:03+00:00",
            }
        ],
        "sentences": [
            {
                "sourceText": "𠮷野に行く。",
                "translatedText": "Going to Yoshino.",
                "createdAt": "2026-09-02T08:02:03+00:00",
            },
            {
                "sourceText": "今日は休みだ。",
                "translatedText": None,
                "createdAt": "2026-09-03T08:02:03+00:00",
            },
        ],
    }


def test_round_trip_preserves_saved_data_without_ids_and_preview_is_read_only(client, tmp_path):
    payload = sample()
    expected = {"wordsAdded": 1, "wordsSkipped": 0, "sentencesAdded": 2, "sentencesSkipped": 0}
    assert client.post("/api/v1/backup/preview", json=payload).json() == expected
    assert api.store.list() == api.store.list_sentences() == []
    assert client.post("/api/v1/backup/restore", json=payload).json() == expected
    exported = client.get("/api/v1/backup")
    assert exported.status_code == 200
    data = exported.json()
    assert data["words"] == payload["words"]
    assert data["sentences"] == payload["sentences"]
    assert "JMdict (EDRDG), CC BY-SA 4.0" in data["dictionaryAttribution"]
    assert all("id" not in row for row in data["words"] + data["sentences"])
    target = VocabularyStore(tmp_path / "other-machine.sqlite3")
    target.restore(parse_backup(exported.content))
    assert target.backup().words == api.store.backup().words
    assert target.backup().sentences == api.store.backup().sentences
    # Dates remain old, not the restore date, and retain newest-first display order.
    assert [s.sourceText for s in target.list_sentences()] == ["今日は休みだ。", "𠮷野に行く。"]


def test_repeated_restore_skips_duplicates_and_preserves_existing_entries(client):
    payload = sample()
    client.post("/api/v1/backup/restore", json=payload)
    original_words = api.store.list()
    original_sentences = api.store.list_sentences()
    payload["words"][0]["meanings"] = ["different meaning"]
    payload["words"][0]["dictionaryForm"] = "違う"
    payload["words"][0]["createdAt"] = "2020-01-01T00:00:00Z"
    payload["sentences"][0]["translatedText"] = "Different translation."
    for endpoint in ["preview", "restore"]:
        response = client.post(f"/api/v1/backup/{endpoint}", json=payload)
        assert response.json() == {
            "wordsAdded": 0,
            "wordsSkipped": 1,
            "sentencesAdded": 0,
            "sentencesSkipped": 2,
        }
    assert api.store.list() == original_words
    assert api.store.list_sentences() == original_sentences


def test_duplicates_inside_backup_match_preview_and_first_entry_wins(client):
    payload = sample()
    payload["words"].append({**payload["words"][0], "meanings": ["different"]})
    payload["sentences"].append({**payload["sentences"][0], "translatedText": "Different."})
    # Another source sentence remains a distinct saved word.
    payload["words"].append({**payload["words"][0], "sourceText": "別の文。"})
    expected = {"wordsAdded": 2, "wordsSkipped": 1, "sentencesAdded": 2, "sentencesSkipped": 1}
    assert client.post("/api/v1/backup/preview", json=payload).json() == expected
    assert client.post("/api/v1/backup/restore", json=payload).json() == expected
    assert all(word.meanings == ["a name", "second meaning"] for word in api.store.list())
    assert api.store.list_sentences()[-1].translatedText == "Going to Yoshino."


def test_restore_rechecks_data_saved_since_preview(client):
    payload = sample()
    assert client.post("/api/v1/backup/preview", json=payload).json()["wordsAdded"] == 1
    api.store.save(
        SaveWordRequest(**{k: v for k, v in payload["words"][0].items() if k != "createdAt"})
    )
    api.store.save_sentence(SaveSentenceRequest(sourceText="𠮷野に行く。"))
    result = client.post("/api/v1/backup/restore", json=payload).json()
    assert result == {
        "wordsAdded": 0,
        "wordsSkipped": 1,
        "sentencesAdded": 1,
        "sentencesSkipped": 1,
    }
    assert api.store.list_sentences()[-1].translatedText is None


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(version=2),
        lambda p: p.update(version=True),
        lambda p: p.update(version="1"),
        lambda p: p.update(format="other-app"),
        lambda p: p.pop("version"),
        lambda p: p.update(extra="not supported"),
        lambda p: p["words"][0].update(id=1),
        lambda p: p["words"][0].update(surface=" " * 3),
        lambda p: p["words"][0].update(meanings=["x" * 2001]),
        lambda p: p["words"][0].update(meanings=[0]),
        lambda p: p["words"][0].update(sourceText="x" * 2001),
        lambda p: p["words"][0].update(createdAt="yesterday"),
        lambda p: p["words"][0].update(createdAt="2026-10-23T10:00:00"),
        lambda p: p["words"][0].update(createdAt="0001-01-01T00:00:00+14:00"),
        lambda p: p["sentences"][0].update(translatedText=" "),
        lambda p: p["sentences"][0].update(translatedText="x" * 4001),
        lambda p: p["sentences"][0].update(sourceText=""),
        lambda p: p["sentences"][0].update(sourceText="\ud800"),
    ],
)
def test_invalid_record_rejects_entire_file_before_writing(client, change):
    payload = sample()
    change(payload)
    for endpoint in ["preview", "restore"]:
        result = client.post(
            f"/api/v1/backup/{endpoint}",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert result.status_code == 422
    assert api.store.list() == api.store.list_sentences() == []


@pytest.mark.parametrize(
    "contents", [b"not JSON", b"[]", b"\xff", b'{"version":1,"version":2}', b'{"version":NaN}']
)
def test_invalid_json_is_rejected(client, contents):
    assert client.post("/api/v1/backup/restore", content=contents).status_code == 422


def test_failed_insert_rolls_back_both_collections(client):
    api.store.list()
    with sqlite3.connect(api.store.path) as connection:
        connection.execute("""CREATE TRIGGER fail_restore BEFORE INSERT ON saved_sentences
                              BEGIN SELECT RAISE(ABORT, 'simulated disk failure'); END""")
    response = client.post("/api/v1/backup/restore", json=sample())
    assert response.status_code == 503
    assert api.store.list() == api.store.list_sentences() == []


def test_size_guard_and_application_headers(client):
    assert (
        client.post("/api/v1/backup/restore", content=b" " * (MAX_BACKUP_BYTES + 1)).status_code
        == 413
    )
    assert (
        client.post(
            "/api/v1/backup/preview", headers={"Content-Length": str(MAX_BACKUP_BYTES + 1)}
        ).status_code
        == 413
    )
    assert client.get("/api/v1/backup", headers={"X-YomiMado-Client": "wrong"}).status_code == 403
    assert (
        client.post(
            "/api/v1/backup/restore", json=sample(), headers={"Origin": "https://example.com"}
        ).status_code
        == 403
    )
    # Backup routes alone have a larger allowance; ordinary JSON limits remain.
    assert client.post("/api/v1/sentences", content=b" " * (1024 * 1024 + 1)).status_code == 413
    payload = sample()
    payload["words"] *= 6000
    body = json.dumps(payload, ensure_ascii=False).encode()
    assert 1024 * 1024 < len(body) < MAX_BACKUP_BYTES
    assert client.post("/api/v1/backup/preview", content=body).json()["wordsSkipped"] == 5999


def test_export_from_existing_database_and_empty_library(client):
    assert client.get("/api/v1/backup").json()["words"] == []
    payload = sample()
    request = copy.deepcopy(payload["words"][0])
    request.pop("createdAt")
    word = api.store.save(SaveWordRequest(**request))
    exported = client.get("/api/v1/backup").json()
    assert exported["words"][0] == word.model_dump(exclude={"id"})
    assert client.post("/api/v1/backup/restore", json=exported).json()["wordsSkipped"] == 1
