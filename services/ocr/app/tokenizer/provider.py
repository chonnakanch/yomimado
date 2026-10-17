"""Select the existing tokenizer or an explicitly enabled development experiment."""

from __future__ import annotations

import os
import sys

from app.tokenizer.sudachi import JapaneseTokenizer, SudachiTokenizer


def get_tokenizer() -> JapaneseTokenizer:
    provider = os.environ.get("YOMIMADO_TOKENIZER", "sudachi")
    if provider == "sudachi":
        return SudachiTokenizer()
    if provider == "lindera":
        if getattr(sys, "frozen", False):
            raise RuntimeError("Lindera is a development experiment, not a packaged tokenizer")
        from app.tokenizer.lindera import LinderaTokenizer

        return LinderaTokenizer()
    raise RuntimeError("Unsupported YOMIMADO_TOKENIZER; choose sudachi or lindera")
