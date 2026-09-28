"""Explicitly saved study words, kept in a local SQLite database."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from os import environ
from pathlib import Path

from app.models import SavedWord, SaveWordRequest


def default_vocabulary_path() -> Path:
    configured = environ.get("YOMIMADO_VOCAB_DB")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        directory = Path.home() / "Library" / "Application Support" / "YomiMado"
    elif sys.platform == "win32":
        directory = Path(environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "YomiMado"
    else:
        directory = Path.home() / ".local" / "share" / "yomimado"
    return directory / "vocabulary.sqlite3"


def _saved_word(row: sqlite3.Row) -> SavedWord:
    return SavedWord(
        id=row["id"],
        surface=row["surface"],
        reading=row["reading"],
        dictionaryForm=row["dictionary_form"],
        meanings=json.loads(row["meanings_json"]),
        sourceText=row["source_text"],
        createdAt=row["created_at"],
    )


class VocabularyStore:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """CREATE TABLE IF NOT EXISTS saved_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surface TEXT NOT NULL,
                reading TEXT NOT NULL,
                dictionary_form TEXT NOT NULL,
                meanings_json TEXT NOT NULL,
                source_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(surface, reading, source_text)
            )"""
        )
        return connection

    def save(self, request: SaveWordRequest) -> SavedWord:
        surface = request.surface.strip()
        reading = request.reading.strip()
        dictionary_form = request.dictionaryForm.strip()
        source_text = request.sourceText.strip()
        if not surface or not dictionary_form or not source_text:
            raise ValueError("A word and source sentence are required")
        meanings = [meaning.strip() for meaning in request.meanings]
        if any(not meaning or len(meaning) > 2000 for meaning in meanings):
            raise ValueError("Each dictionary meaning must contain 1–2000 characters")
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO saved_words
                   (surface, reading, dictionary_form, meanings_json, source_text, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(surface, reading, source_text)
                   DO UPDATE SET dictionary_form = excluded.dictionary_form,
                                 meanings_json = excluded.meanings_json""",
                (
                    surface,
                    reading,
                    dictionary_form,
                    json.dumps(meanings, ensure_ascii=False),
                    source_text,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            row = connection.execute(
                """SELECT * FROM saved_words
                   WHERE surface = ? AND reading = ? AND source_text = ?""",
                (surface, reading, source_text),
            ).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("Saved word could not be read back")
            return _saved_word(row)

    def list(self) -> list[SavedWord]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT * FROM saved_words ORDER BY created_at DESC, id DESC"
            ).fetchall()
            return [_saved_word(row) for row in rows]

    def delete(self, word_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            result = connection.execute("DELETE FROM saved_words WHERE id = ?", (word_id,))
            return result.rowcount > 0
