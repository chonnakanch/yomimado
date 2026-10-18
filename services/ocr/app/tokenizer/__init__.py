"""Application tokenizer contract, independent of native engine packages."""

from typing import Protocol

from app.models import TextToken


class JapaneseTokenizer(Protocol):
    """Port for learning analysis; implementations own engine details/resources.

    Return ordered, non-overlapping TextTokens whose code-point spans reference
    the unchanged input. Omit symbol-only tokens, preserve unknown surfaces and
    raise RuntimeError when analysis is unavailable or native output is invalid.
    """

    def tokenize(self, text: str) -> list[TextToken]: ...
