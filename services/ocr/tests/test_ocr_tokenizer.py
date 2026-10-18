import sys
from types import SimpleNamespace

from app.pipeline.ocr_tokenizer import load_ocr_tokenizer


def test_ocr_decode_loader_disables_dictionary_initialization_without_global_changes(monkeypatch):
    calls = []
    loader = SimpleNamespace(from_pretrained=lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=loader))
    load_ocr_tokenizer("local/model", do_word_tokenize=True)
    assert calls == [
        (
            ("local/model",),
            {
                "do_word_tokenize": False,
                "word_tokenizer_type": "basic",
                "tokenizer_type": "bert-japanese",
                "local_files_only": True,
            },
        )
    ]
    assert sys.modules["transformers"].AutoTokenizer is loader
