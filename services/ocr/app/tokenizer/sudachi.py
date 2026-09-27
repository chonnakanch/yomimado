from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from app.models import TextToken


class JapaneseTokenizer(Protocol):
    def tokenize(self, text: str) -> list[TextToken]: ...


def _offsets(text: str, surface: str, begin: int, end: int) -> tuple[int, int]:
    """Return Python string offsets, accepting Sudachi's byte or character indices."""
    if text[begin:end] == surface:
        return begin, end

    encoded = text.encode("utf-8")
    try:
        if encoded[begin:end].decode("utf-8") == surface:
            return len(encoded[:begin].decode("utf-8")), len(encoded[:end].decode("utf-8"))
    except UnicodeDecodeError:
        pass

    raise ValueError("Sudachi token offsets do not match the original text")


@lru_cache(maxsize=1)
def _dictionary():
    try:
        from sudachipy import dictionary
    except ImportError as error:
        raise RuntimeError(
            "Japanese tokenization is unavailable. Install pip extra '[tokenization]' "
            "in the OCR service environment."
        ) from error

    try:
        return dictionary.Dictionary(dict="core")
    except Exception as error:
        raise RuntimeError("Sudachi core dictionary could not be loaded") from error


class SudachiTokenizer:
    def tokenize(self, text: str) -> list[TextToken]:
        from sudachipy import tokenizer

        # A tokenizer is made per request; the dictionary remains cached. Sudachi
        # does not allow concurrent calls on one tokenizer instance.
        morphemes = _dictionary().create().tokenize(text, tokenizer.Tokenizer.SplitMode.C)
        tokens: list[TextToken] = []
        for morpheme in morphemes:
            surface = morpheme.surface()
            start, end = _offsets(text, surface, morpheme.begin(), morpheme.end())
            tokens.append(
                TextToken(
                    surface=surface,
                    reading=morpheme.reading_form() or surface,
                    dictionaryForm=morpheme.dictionary_form() or surface,
                    start=start,
                    end=end,
                    partOfSpeech=" / ".join(
                        part for part in morpheme.part_of_speech() if part != "*"
                    ),
                )
            )
        return tokens
