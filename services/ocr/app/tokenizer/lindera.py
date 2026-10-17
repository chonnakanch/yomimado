"""Opt-in Lindera/IPADIC development experiment; release bundles still use Sudachi."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from app.models import TextToken

INPUTS = Path(__file__).resolve().parents[2] / "lindera-experiment-inputs.json"


def verify_dictionary(path: Path, expected: dict[str, str]) -> None:
    if not path.is_dir() or {p.name for p in path.iterdir()} != set(expected):
        raise RuntimeError("Lindera requires the exact experimental IPADIC file set")
    for name, sha in expected.items():
        source = path / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("Lindera dictionary contains an unexpected link or directory")
        with source.open("rb") as stream:
            actual = hashlib.sha256(stream.read()).hexdigest()
        if actual != sha:
            raise RuntimeError(f"Lindera experimental dictionary checksum differs: {name}")


@lru_cache(maxsize=1)
def _backend(path: str):
    pins = json.loads(INPUTS.read_text())
    try:
        if importlib.metadata.version("lindera") != pins["version"]:
            raise RuntimeError("This experiment requires lindera==6.0.0")
        from lindera import TokenizerBuilder
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        raise RuntimeError("Install the pinned Lindera experiment wheel first") from error
    verify_dictionary(Path(path), pins["dictionary"]["files"])
    try:
        builder = TokenizerBuilder()
        builder.set_dictionary(path)
        builder.set_mode("normal")
        # No normalization, base-form replacement, stop-word or reading filters:
        # surfaces and offsets must continue to refer to the original OCR string.
        return builder.build(), Lock()
    except Exception as error:
        raise RuntimeError("Lindera could not load the experimental IPADIC dictionary") from error


def _character_offsets(text: str) -> dict[int, int]:
    offsets = {0: 0}
    byte = 0
    for index, character in enumerate(text):
        byte += len(character.encode("utf-8"))
        offsets[byte] = index + 1
    return offsets


class LinderaTokenizer:
    def tokenize(self, text: str) -> list[TextToken]:
        configured = os.environ.get("YOMIMADO_LINDERA_DICTIONARY")
        if not configured:
            raise RuntimeError(
                "Set YOMIMADO_LINDERA_DICTIONARY to the experimental IPADIC directory"
            )
        path = Path(configured).expanduser().resolve()
        backend, lock = _backend(str(path))
        try:
            # Serialize calls to a cached native tokenizer rather than assuming
            # its Python binding accepts concurrent mutable borrows.
            with lock:
                raw = [token.to_dict() for token in backend.tokenize(text)]
        except Exception as error:
            raise RuntimeError("Lindera tokenization failed") from error
        offsets = _character_offsets(text)
        tokens = []
        previous_end = 0
        for token in raw:
            try:
                surface = token["surface"]
                start = offsets[token["byte_start"]]
                end = offsets[token["byte_end"]]
                details = token["details"]
                unknown = token["is_unknown"]
                if start < previous_end or end <= start or text[start:end] != surface:
                    raise ValueError("Invalid span")
                previous_end = end
                if not any(character.isalnum() for character in surface):
                    continue
                if not isinstance(details, list) or not all(isinstance(x, str) for x in details):
                    raise ValueError("Invalid features")
                if not unknown and len(details) != 9:
                    raise ValueError("Unexpected IPADIC schema")
                base = details[6] if len(details) > 6 and details[6] not in ("", "*") else surface
                reading = (
                    details[7] if len(details) > 7 and details[7] not in ("", "*") else surface
                )
                tokens.append(
                    TextToken(
                        surface=surface,
                        reading=reading,
                        dictionaryForm=base,
                        start=start,
                        end=end,
                        partOfSpeech=" / ".join(value for value in details[:6] if value != "*"),
                    )
                )
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise RuntimeError(
                    "Lindera returned incompatible features or text offsets"
                ) from error
        return tokens
