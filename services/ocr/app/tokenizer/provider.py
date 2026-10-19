"""Select Lindera/IPADIC, retaining Sudachi only for development comparisons."""

from __future__ import annotations

import os
import sys

from app.tokenizer import JapaneseTokenizer


def get_tokenizer() -> JapaneseTokenizer:
    provider = os.environ.get("YOMIMADO_TOKENIZER", "lindera")
    if provider == "sudachi":
        if getattr(sys, "frozen", False):
            raise RuntimeError("Sudachi is available only for development comparisons")
        from app.tokenizer.sudachi import SudachiTokenizer

        return SudachiTokenizer()
    if provider == "lindera":
        from app.tokenizer.lindera import LinderaTokenizer

        return LinderaTokenizer()
    raise RuntimeError("Unsupported YOMIMADO_TOKENIZER; choose sudachi or lindera")
