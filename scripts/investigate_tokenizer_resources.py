"""Offline, source-only experiment; does not modify runtime or packaging inputs.

Compare the existing OCR tokenizer with do_word_tokenize=False in separate
processes. Candidate workers reject UniDic/Fugashi imports. Use only the checked-in
synthetic OCR images and a locally provided Japanese font. Not a release gate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import pickle
import platform
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TEXTS = (
    "今日は学校に行きたくない。🙂!?",
    "無理のしすぎはダメだよ〜",
    "食べました。食べた。食べない。",
    "東京都で待ち合わせしよう。",
    "ドラゴンボールを読んでいる。",
    "お兄ちゃん、待って！",
    "取り戻せないものもある。",
    "ABC１２３…・・!?",
)
DRAW_TEXTS = ("今日は学校に行きます。", "無理はダメだよ", "食べました", "お兄ちゃん！")
SUDACHI_TEXTS = TEXTS + (
    "東京スカイツリーに行った。",
    "東京ディズニーランドで遊んだ。",
    "週刊少年ジャンプを買った。",
    "鬼滅の刃を読んだ。",
    "呪術廻戦が好きです。",
    "進撃の巨人の話をしよう。",
    "孫悟空とベジータが戦う。",
    "竈門炭治郎が走り出した。",
    "秋葉原駅で待っている。",
    "関西国際空港に着いた。",
    "国際連合安全保障理事会の会議。",
    "スターバックスでコーヒーを飲む。",
    "スマートフォンを買い替えたい。",
    "取り返しのつかないことをした。",
    "食べさせられなかった。",
    "行かなきゃいけないんだ。",
    "何やってんだよ、ふざけんな！",
    "そんなこと言われても困っちゃう。",
    "山田太郎さんと鈴木花子さん。",
    "私は読み窓を使っています。",
    "ＡＢＣ１２３とABC123。",
    "🙂学校で勉強する。\n明日も頑張ろう。",
    "日本経済新聞を読む。",
    "全国高等学校野球選手権大会に出場する。",
)


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reject_ocr_dictionaries(event, arguments):
    if event == "import" and arguments[0].split(".")[0] in {
        "unidic_lite",
        "unidic",
        "fugashi",
        "MeCab",
    }:
        raise ImportError("Candidate must not import " + arguments[0])


def worker(args) -> dict:
    if args.worker == "without-unidic":
        sys.addaudithook(reject_ocr_dictionaries)
    import torch
    from manga_ocr import ocr as manga
    from PIL import Image, ImageDraw, ImageFont
    from transformers import AutoTokenizer

    torch.set_num_threads(2)
    candidate = args.worker == "without-unidic"
    # The pinned tokenizer's pickle methods assume a word tokenizer exists when
    # its type is "mecab", even with word tokenization disabled. "basic" avoids
    # that assumption; do_word_tokenize=False still prevents creating one.
    options = (
        {"do_word_tokenize": False, "word_tokenizer_type": "basic"} if candidate else {}
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, tokenizer_type="bert-japanese", local_files_only=True, **options
    )
    if hasattr(tokenizer, "word_tokenizer") == candidate:
        raise RuntimeError("Word tokenizer initialization did not match the experiment")

    # Compare every vocabulary ID with and without special-token filtering, plus
    # deterministic mixed sequences that exercise spaces, specials and cleanup.
    rng = random.Random(20261017)
    cases = [[index] for index in range(len(tokenizer))]
    cases += [[], tokenizer.all_special_ids]
    cases += [
        [rng.randrange(len(tokenizer)) for _ in range(rng.randrange(1, 301))]
        for _ in range(256)
    ]
    decoded = [
        tokenizer.decode(ids, skip_special_tokens=skip)
        for skip in (False, True)
        for ids in cases
    ]
    restored = pickle.loads(pickle.dumps(tokenizer))
    if restored.get_vocab() != tokenizer.get_vocab() or any(
        restored.decode(ids, skip_special_tokens=True)
        != tokenizer.decode(ids, skip_special_tokens=True)
        for ids in cases[-258:]
    ):
        raise RuntimeError("Tokenizer serialization changed vocabulary or decoding")
    # Affect the local Manga OCR constructor only, without editing installed code,
    # the model tokenizer_config.json, or either production application adapter.
    original_loader = AutoTokenizer.from_pretrained

    def loader(*values, **kwargs):
        return original_loader(
            *values, **(kwargs | options | {"local_files_only": True})
        )

    manga.AutoTokenizer = SimpleNamespace(from_pretrained=loader)
    recognizer = manga.MangaOcr(str(args.model), force_cpu=True)
    if hasattr(recognizer.tokenizer, "word_tokenizer") == candidate:
        raise RuntimeError("Manga OCR did not use the expected tokenizer")
    images = {
        name: Image.open(ROOT / f"scripts/fixtures/windows-ocr-{name}.png").copy()
        for name in ("horizontal", "vertical")
    }
    font = ImageFont.truetype(str(args.font), 40)
    for index, text in enumerate(DRAW_TEXTS):
        for vertical in (False, True):
            width, height = (
                (90, 40 + 50 * len(text)) if vertical else (40 + 45 * len(text), 100)
            )
            image = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(image)
            if vertical:
                for offset, character in enumerate(text):
                    draw.text(
                        (20, 20 + 50 * offset),
                        character,
                        font=font,
                        fill="black",
                        anchor="lt",
                    )
            else:
                draw.text((20, 20), text, font=font, fill="black", anchor="lt")
            images[f"generated-{index}-{'vertical' if vertical else 'horizontal'}"] = (
                image
            )
    results = {name: recognizer(image) for name, image in images.items()}
    if not all(results.values()) or "学校" not in results["horizontal"]:
        raise RuntimeError("Recognition fixtures did not produce meaningful output")

    sys.path.insert(0, str(ROOT / "services/ocr"))
    from app.tokenizer.sudachi import SudachiTokenizer

    analysis = {
        text: [token.model_dump() for token in SudachiTokenizer().tokenize(text)]
        for text in TEXTS
    }
    if not all(
        text[token["start"] : token["end"]] == token["surface"]
        for text, tokens in analysis.items()
        for token in tokens
    ):
        raise RuntimeError("Sudachi token offsets do not match original text")
    return {
        "worker": args.worker,
        "vocabularyEntries": len(tokenizer),
        "vocabularySha256": fingerprint(tokenizer.get_vocab()),
        "decoderCases": len(decoded),
        "decodedSha256": fingerprint(decoded),
        "hasWordTokenizer": hasattr(tokenizer, "word_tokenizer"),
        "tokenizerOptions": options,
        "pickleRoundTrip": True,
        "ocr": results,
        "sudachi": analysis,
        "ocrDictionaryImports": sorted(
            name
            for name in sys.modules
            if name.split(".")[0] in {"unidic_lite", "unidic", "fugashi", "MeCab"}
        ),
    }


def compare(results: dict) -> dict:
    baseline, candidate = results["baseline"], results["without-unidic"]
    checks = {
        "sameVocabulary": baseline["vocabularySha256"] == candidate["vocabularySha256"],
        "sameDecodedText": baseline["decodedSha256"] == candidate["decodedSha256"],
        "sameRecognizedText": baseline["ocr"] == candidate["ocr"],
        "sameSudachiAnalysis": baseline["sudachi"] == candidate["sudachi"],
        "serializationPreserved": baseline["pickleRoundTrip"]
        and candidate["pickleRoundTrip"],
        "candidateAvoidsOcrDictionaries": not candidate["ocrDictionaryImports"]
        and not candidate["hasWordTokenizer"],
    }
    return {"checks": checks, "passed": all(checks.values())}


def compare_sudachi(small_path: Path) -> dict:
    """Measure behavior differences; no claim that changed segmentation is wrong."""
    from unittest.mock import patch

    from sudachipy import dictionary

    sys.path.insert(0, str(ROOT / "services/ocr"))
    from app.tokenizer import sudachi

    results = {}
    for name, resource in (
        ("core", dictionary.Dictionary(dict="core")),
        ("small", dictionary.Dictionary(dict=str(small_path.resolve()))),
    ):
        with patch.object(sudachi, "_dictionary", return_value=resource):
            results[name] = {
                text: [
                    token.model_dump()
                    for token in sudachi.SudachiTokenizer().tokenize(text)
                ]
                for text in SUDACHI_TEXTS
            }
        resource.close()
    differences = {
        text: {edition: results[edition][text] for edition in results}
        for text in SUDACHI_TEXTS
        if results["core"][text] != results["small"][text]
    }
    return {
        "testedSentences": len(SUDACHI_TEXTS),
        "changedSentences": len(differences),
        "smallDictionarySha256": file_hash(small_path),
        "smallDictionaryBytes": small_path.stat().st_size,
        "differences": differences,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--sudachi-small", type=Path, help="Optional isolated Small .dic to compare"
    )
    parser.add_argument("--worker", choices=("baseline", "without-unidic"))
    args = parser.parse_args()
    if args.worker:
        args.output.write_text(
            json.dumps(worker(args), ensure_ascii=False, indent=2) + "\n"
        )
        return
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "comparison.json").unlink(missing_ok=True)
    results = {}
    for mode in ("baseline", "without-unidic"):
        destination = args.output / f"{mode}.json"
        with (args.output / f"{mode}.log").open("w") as log:
            subprocess.run(
                [
                    sys.executable,
                    __file__,
                    "--worker",
                    mode,
                    "--model",
                    str(args.model.resolve()),
                    "--font",
                    str(args.font.resolve()),
                    "--output",
                    str(destination.resolve()),
                ],
                env=os.environ | {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        results[mode] = json.loads(destination.read_text())
    report = compare(results) | {
        "scope": "source-only tokenizer experiment; not frozen or installed-app verification",
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "versions": {
            name: importlib.metadata.version(name)
            for name in (
                "manga-ocr",
                "transformers",
                "torch",
                "Pillow",
                "SudachiPy",
                "SudachiDict-core",
                "unidic-lite",
            )
        },
        "inputSha256": {
            name: file_hash(args.model / name)
            for name in (
                "pytorch_model.bin",
                "config.json",
                "tokenizer_config.json",
                "vocab.txt",
                "preprocessor_config.json",
            )
        }
        | {"font": file_hash(args.font), "probe": file_hash(Path(__file__))},
        "results": results,
    }
    if args.sudachi_small:
        report["sudachiSmallComparison"] = compare_sudachi(args.sudachi_small)
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({key: report[key] for key in ("passed", "checks")}, indent=2))
    if not report["passed"]:
        raise SystemExit("Tokenizer parity failed; inspect comparison.json")


if __name__ == "__main__":
    main()
