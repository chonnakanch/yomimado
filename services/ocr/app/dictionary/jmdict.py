"""Indexed, offline English word lookup from a user-installed JMdict file."""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import threading
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

from app.models import WordEntry, WordSense

DICTIONARY_DIR = Path(__file__).resolve().parents[2] / "local-dictionaries"
DEFAULT_PATH = DICTIONARY_DIR / "JMdict_e.gz"
DEFAULT_INDEX_PATH = DICTIONARY_DIR / "jmdict-index.sqlite3"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SCHEMA_VERSION = 1
_index_lock = threading.Lock()


def _paths() -> tuple[Path, Path]:
    source = Path(os.environ.get("YOMIMADO_JMDICT", str(DEFAULT_PATH))).expanduser()
    index = Path(os.environ.get("YOMIMADO_JMDICT_INDEX", str(DEFAULT_INDEX_PATH))).expanduser()
    return source, index


def _hiragana(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return "".join(
        chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character
        for character in normalized
    )


def _entry_data(element: ElementTree.Element) -> dict:
    kanji = [
        {"text": item.findtext("keb"), "common": item.find("ke_pri") is not None}
        for item in element.findall("k_ele")
        if item.findtext("keb")
    ]
    readings = [
        {
            "text": item.findtext("reb"),
            "common": item.find("re_pri") is not None,
            "noKanji": item.find("re_nokanji") is not None,
            "restrictions": [restricted.text for restricted in item.findall("re_restr")],
        }
        for item in element.findall("r_ele")
        if item.findtext("reb")
    ]
    senses = []
    for item in element.findall("sense"):
        glosses = [
            gloss.text
            for gloss in item.findall("gloss")
            if gloss.text and gloss.get(XML_LANG) in (None, "en", "eng")
        ]
        if glosses:
            senses.append(
                {
                    "glosses": glosses,
                    "kanjiRestrictions": [value.text for value in item.findall("stagk")],
                    "readingRestrictions": [value.text for value in item.findall("stagr")],
                }
            )
    return {"kanji": kanji, "readings": readings, "senses": senses}


def _build_index(connection: sqlite3.Connection, source: Path, fingerprint: str) -> None:
    opener = gzip.open if source.suffix == ".gz" else open
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DROP TABLE IF EXISTS forms")
        connection.execute("DROP TABLE IF EXISTS entries")
        connection.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute("CREATE TABLE forms (form TEXT NOT NULL, entry_id INTEGER NOT NULL)")
        with opener(source, "rb") as stream:
            events = ElementTree.iterparse(stream, events=("start", "end"))
            _, root = next(events)
            for event, element in events:
                if event != "end" or element.tag != "entry":
                    continue
                entry = _entry_data(element)
                if entry["senses"]:
                    cursor = connection.execute(
                        "INSERT INTO entries (payload) VALUES (?)",
                        (json.dumps(entry, ensure_ascii=False),),
                    )
                    forms = {item["text"] for item in entry["kanji"] + entry["readings"]}
                    connection.executemany(
                        "INSERT INTO forms (form, entry_id) VALUES (?, ?)",
                        ((form, cursor.lastrowid) for form in forms),
                    )
                root.clear()
        connection.execute("CREATE INDEX forms_by_form ON forms (form)")
        connection.execute("DELETE FROM metadata")
        connection.execute(
            "INSERT INTO metadata (fingerprint, schema_version) VALUES (?, ?)",
            (fingerprint, SCHEMA_VERSION),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _connection() -> sqlite3.Connection:
    source, index = _paths()
    if not source.is_file():
        raise FileNotFoundError(
            f"JMdict is not installed. Put JMdict_e.gz at {source} "
            "or set YOMIMADO_JMDICT to its absolute path, then restart the OCR service."
        )
    index.parent.mkdir(parents=True, exist_ok=True)
    source_stat = source.stat()
    fingerprint = f"{source.resolve()}:{source_stat.st_size}:{source_stat.st_mtime_ns}"
    with _index_lock:
        connection = sqlite3.connect(index, timeout=30)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS metadata (fingerprint TEXT, schema_version INTEGER)"
            )
            current = connection.execute(
                "SELECT fingerprint, schema_version FROM metadata LIMIT 1"
            ).fetchone()
            if current != (fingerprint, SCHEMA_VERSION):
                _build_index(connection, source, fingerprint)
            return connection
        except Exception:
            connection.close()
            raise


def _candidate(
    entry: dict, form: str, requested_reading: str, match: str
) -> tuple[int, WordEntry] | None:
    kanji_form = next((item for item in entry["kanji"] if item["text"] == form), None)
    reading_form = next((item for item in entry["readings"] if item["text"] == form), None)
    if kanji_form is None and reading_form is None:
        return None
    applicable = (
        [
            item
            for item in entry["readings"]
            if not item["noKanji"] and (not item["restrictions"] or form in item["restrictions"])
        ]
        if kanji_form is not None
        else [item for item in entry["readings"] if item["text"] == form]
    )
    if not applicable:
        return None
    chosen = next(
        (item for item in applicable if _hiragana(item["text"]) == _hiragana(requested_reading)),
        applicable[0],
    )
    senses = [
        WordSense(glosses=sense["glosses"][:5])
        for sense in entry["senses"]
        if (not sense["kanjiRestrictions"] or form in sense["kanjiRestrictions"])
        and (not sense["readingRestrictions"] or chosen["text"] in sense["readingRestrictions"])
    ]
    if not senses:
        return None
    reading_match = bool(requested_reading) and _hiragana(chosen["text"]) == _hiragana(
        requested_reading
    )
    common = bool((kanji_form or reading_form)["common"] or chosen["common"])
    score = (4 if match == "surface" else 0) + (2 if reading_match else 0) + (1 if common else 0)
    return score, WordEntry(
        expression=form,
        reading=chosen["text"],
        senses=senses[:5],
        match=match,
        readingMatch=reading_match,
        common=common,
    )


def lookup(surface: str, dictionary_form: str, reading: str) -> list[WordEntry]:
    connection = _connection()
    try:
        found: list[tuple[int, WordEntry]] = []
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        for form, match in [(surface, "surface"), (dictionary_form, "dictionaryForm")]:
            if match == "dictionaryForm" and form == surface:
                continue
            rows = connection.execute(
                "SELECT e.payload FROM forms f JOIN entries e ON e.id = f.entry_id "
                "WHERE f.form = ? LIMIT 200",
                (form,),
            )
            for (payload,) in rows:
                candidate = _candidate(json.loads(payload), form, reading, match)
                if candidate is None:
                    continue
                _, result = candidate
                key = (
                    result.expression,
                    result.reading,
                    tuple(gloss for sense in result.senses for gloss in sense.glosses),
                )
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
        found.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in found[:3]]
    finally:
        connection.close()
