"""Read user-installed KANJIDIC2 data without bundling dictionary assets."""

from __future__ import annotations

import gzip
import os
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from app.models import KanjiEntry

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "local-dictionaries" / "kanjidic2.xml.gz"


def dictionary_path() -> Path:
    configured = os.environ.get("YOMIMADO_KANJIDIC2")
    return Path(configured).expanduser() if configured else DEFAULT_PATH


@lru_cache(maxsize=2)
def _load(path: Path) -> dict[str, KanjiEntry]:
    if not path.is_file():
        raise FileNotFoundError(
            f"KANJIDIC2 is not installed. Put kanjidic2.xml.gz at {path} "
            "or set YOMIMADO_KANJIDIC2 to its absolute path, then restart the OCR service."
        )
    entries: dict[str, KanjiEntry] = {}
    open_file = gzip.open if path.suffix == ".gz" else open
    with open_file(path, "rb") as source:
        events = ElementTree.iterparse(source, events=("start", "end"))
        _, root = next(events)
        for event, element in events:
            if event != "end" or element.tag != "character":
                continue
            literal = element.findtext("literal")
            if literal:
                group = element.find("reading_meaning/rmgroup")
                readings = group.findall("reading") if group is not None else []
                entries[literal] = KanjiEntry(
                    character=literal,
                    onReadings=[r.text for r in readings if r.get("r_type") == "ja_on" and r.text],
                    kunReadings=[
                        r.text for r in readings if r.get("r_type") == "ja_kun" and r.text
                    ],
                    meanings=[
                        m.text
                        for m in group.findall("meaning")
                        if m.get("m_lang") in (None, "en") and m.text
                    ]
                    if group is not None
                    else [],
                )
            root.clear()
    return entries


def lookup(character: str) -> KanjiEntry | None:
    return _load(dictionary_path()).get(character)
