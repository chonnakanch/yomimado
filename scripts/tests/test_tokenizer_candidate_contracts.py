from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services/ocr"))
from compare_tokenizer_candidates import (
    MeCabAdapter,
    check_targets,
    make_token,
    validate_tokens,
)


class CandidateContractTests(unittest.TestCase):
    def test_repeated_words_keep_positions_after_emoji_and_whitespace(self):
        node = lambda surface, gap="": SimpleNamespace(
            surface=surface,
            white_space=gap,
            feature=("名詞", "一般", "*", "*", "*", "*", surface, "ガッコウ"),
        )
        text = "🙂学校 \t学校\n"
        adapter = MeCabAdapter(
            lambda _: [node("🙂"), node("学校"), node("学校", " \t")]
        )
        tokens = [x.model_dump() for x in adapter.tokenize(text)]
        validate_tokens(text, tokens)
        self.assertEqual([(x["start"], x["end"]) for x in tokens], [(1, 3), (5, 7)])

    def test_mecab_cannot_skip_non_whitespace_at_end(self):
        with self.assertRaisesRegex(ValueError, "unaccounted"):
            MeCabAdapter(lambda _: []).tokenize("学校")

    def test_mecab_cannot_silently_shift_a_node(self):
        node = SimpleNamespace(surface="学校", white_space=" ", feature=("名詞",) * 9)
        with self.assertRaisesRegex(ValueError, "whitespace"):
            MeCabAdapter(lambda _: [node]).tokenize("🙂学校")

    def test_byte_offsets_cannot_masquerade_as_character_offsets(self):
        with self.assertRaisesRegex(ValueError, "original source span"):
            make_token("🙂学校", "学校", 4, 10, "ガッコウ", "学校", "名詞")

    def test_missing_lemma_does_not_pass_inflected_base_form_check(self):
        token = make_token("食べ", "食べ", 0, 2, "タベ", None, "動詞")
        result = check_targets(
            {"食べ": [token.model_dump()]}, [("食べ", "食べ", "タベ", "食べる")]
        )[0]
        self.assertTrue(result["surfaceAndReading"])
        self.assertFalse(result["surfaceAndBase"])
        self.assertFalse(result["allFields"])

    def test_pronunciation_is_not_silently_changed_to_a_dictionary_reading(self):
        token = make_token("学校", "学校", 0, 2, "ガッコー", None, "名詞")
        result = check_targets(
            {"学校": [token.model_dump()]}, [("学校", "学校", "ガッコウ", "学校")]
        )[0]
        self.assertTrue(result["surfaceAndBase"])
        self.assertFalse(result["surfaceAndReading"])

    def test_legitimate_lemma_variant_is_accepted(self):
        token = make_token("信じ", "信じ", 0, 2, "シンジ", "信ずる", "動詞")
        result = check_targets(
            {"信じ": [token.model_dump()]}, [("信じ", "信じ", "シンジ", "信じる")]
        )[0]
        self.assertTrue(result["allFields"])


if __name__ == "__main__":
    unittest.main()
