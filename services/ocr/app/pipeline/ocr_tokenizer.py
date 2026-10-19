"""Decode generated OCR IDs with the model's vocabulary, without MeCab data."""


def load_ocr_tokenizer(model, **kwargs):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        model,
        **(
            kwargs
            | {
                "tokenizer_type": "bert-japanese",
                "local_files_only": True,
                "do_word_tokenize": False,
                "word_tokenizer_type": "basic",
            }
        ),
    )
