"""Offline development comparison: Sudachi Core, optional Small and Lindera/IPADIC.

Requires the isolated Lindera site on PYTHONPATH and a verified dictionary.
Writes synthetic-text reports and a rebuildable JMdict index under --output.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from investigate_tokenizer_resources import SUDACHI_TEXTS

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("今日は学校に行きます。", "今日", "キョウ", "今日"),
    ("学校へ行った。", "行っ", "イッ", "行く"),
    ("食べました。", "食べ", "タベ", "食べる"),
    ("待ってください。", "待っ", "マッ", "待つ"),
    ("本を読んでいる。", "読ん", "ヨン", "読む"),
    ("映画を見ました。", "見", "ミ", "見る"),
    ("🙂学校で勉強する。", "学校", "ガッコウ", "学校"),
    ("お兄ちゃん、待って！", "お兄ちゃん", "オニイチャン", "お兄ちゃん"),
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def size(path: Path) -> int:
    return sum(
        p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--jmdict", type=Path, required=True)
    parser.add_argument(
        "--sudachi-small", type=Path, help="Optional exact 20250515 Small dictionary"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=25)
    parser.add_argument("--require-learning-parity", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.sudachi_small:
        expected_small = (
            "2cc37253779a4668815c9c2c019057de8f698675fb57d85ddd7731ab3f6d90b3"
        )
        if digest(args.sudachi_small) != expected_small:
            parser.error(
                "--sudachi-small must be the verified Sudachi Small 20250515 dictionary"
            )
        if importlib.metadata.version("SudachiPy") != "0.6.10":
            parser.error("The Small comparison requires the baseline SudachiPy 0.6.10")
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        {
            "YOMIMADO_LINDERA_DICTIONARY": str(args.dictionary.resolve()),
            "YOMIMADO_JMDICT": str(args.jmdict.resolve()),
            "YOMIMADO_JMDICT_INDEX": str(
                (args.output / "jmdict-index.sqlite3").resolve()
            ),
        }
    )
    sys.path.insert(0, str(ROOT / "services/ocr"))
    from app.dictionary.jmdict import lookup
    from app.tokenizer.lindera import LinderaTokenizer
    from app.tokenizer.sudachi import SudachiTokenizer

    providers = {"sudachi": SudachiTokenizer(), "lindera": LinderaTokenizer()}
    small_resource = None
    if args.sudachi_small:
        providers["sudachi-small"] = SudachiTokenizer()
    corpus = tuple(dict.fromkeys((*SUDACHI_TEXTS, *(x[0] for x in CHECKS))))
    results = {}
    for name, tokenizer in providers.items():
        load_seconds = 0.0
        if name == "sudachi-small":
            from sudachipy import dictionary

            start = time.perf_counter()
            small_resource = dictionary.Dictionary(
                dict=str(args.sudachi_small.resolve())
            )
            load_seconds = time.perf_counter() - start
        context = (
            patch(
                "app.tokenizer.sudachi._dictionary",
                new=lambda resource=small_resource: resource,
            )
            if name == "sudachi-small"
            else nullcontext()
        )
        with context:
            start = time.perf_counter()
            tokenizer.tokenize(corpus[0])
            initialization = load_seconds + time.perf_counter() - start
            analyzed = {
                text: [token.model_dump() for token in tokenizer.tokenize(text)]
                for text in corpus
            }
            offsets = all(
                text[x["start"] : x["end"]] == x["surface"]
                for text, tokens in analyzed.items()
                for x in tokens
            )
            golden = [
                {
                    "text": text,
                    "expected": {
                        "surface": surface,
                        "reading": reading,
                        "dictionaryForm": base,
                    },
                    "passed": any(
                        (x["surface"], x["reading"], x["dictionaryForm"])
                        == (surface, reading, base)
                        for x in analyzed[text]
                    ),
                }
                for text, surface, reading, base in CHECKS
            ]
            durations = []
            for _ in range(args.repeats):
                for text in corpus:
                    start = time.perf_counter()
                    tokenizer.tokenize(text)
                    durations.append((time.perf_counter() - start) * 1000)
            words = [token for tokens in analyzed.values() for token in tokens]
            found = [
                lookup(x["surface"], x["dictionaryForm"], x["reading"]) for x in words
            ]
            results[name] = {
                "sentences": analyzed,
                "validOffsets": offsets,
                "learningChecks": golden,
                "tokenCount": len(words),
                "tokensWithDictionaryMatch": sum(bool(x) for x in found),
                "tokensWithReadingMatch": sum(
                    any(e.readingMatch for e in x) for x in found
                ),
                "initializationSeconds": initialization,
                "warmMedianMs": statistics.median(durations),
                "warmP95Ms": sorted(durations)[int(0.95 * (len(durations) - 1))],
                "timingCalls": len(durations),
                "timingSamplesMs": durations,
            }
    if small_resource is not None:
        small_resource.close()
    differences = {
        text: {key: results[key]["sentences"][text] for key in providers}
        for text in corpus
        if [
            (x["surface"], x["reading"], x["dictionaryForm"])
            for x in results["sudachi"]["sentences"][text]
        ]
        != [
            (x["surface"], x["reading"], x["dictionaryForm"])
            for x in results["lindera"]["sentences"][text]
        ]
    }
    import lindera
    import sudachidict_core
    import sudachipy

    sizes = {
        "linderaDictionaryBytes": size(args.dictionary),
        "linderaPackageBytes": size(Path(lindera.__file__).parent),
        "sudachiDictionaryBytes": size(Path(sudachidict_core.__file__).parent),
        "sudachiPackageBytes": size(Path(sudachipy.__file__).parent),
    }
    if args.sudachi_small:
        sizes["sudachiSmallDictionaryBytes"] = args.sudachi_small.stat().st_size
    differences_by_provider = {}
    for name in providers:
        if name == "sudachi":
            continue
        differences_by_provider[name] = {
            text: {key: results[key]["sentences"][text] for key in ("sudachi", name)}
            for text in corpus
            if [
                (x["surface"], x["reading"], x["dictionaryForm"])
                for x in results["sudachi"]["sentences"][text]
            ]
            != [
                (x["surface"], x["reading"], x["dictionaryForm"])
                for x in results[name]["sentences"][text]
            ]
        }
    pins = ROOT / "services/ocr/lindera-experiment-inputs.json"
    report = {
        "scope": "development experiment; no frozen-service or installed-app claim",
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "versions": {
            x: importlib.metadata.version(x)
            for x in ("lindera", "SudachiPy", "SudachiDict-core")
        },
        "inputSha256": {
            "manifest": digest(pins),
            "jmdict": digest(args.jmdict),
            "benchmark": digest(Path(__file__)),
            "corpusSource": digest(ROOT / "scripts/investigate_tokenizer_resources.py"),
            "adapter": digest(ROOT / "services/ocr/app/tokenizer/lindera.py"),
            "sudachiAdapter": digest(ROOT / "services/ocr/app/tokenizer/sudachi.py"),
            "sudachiCoreDictionary": digest(
                Path(sudachidict_core.__file__).parent / "resources/system.dic"
            ),
            **(
                {"sudachiSmallDictionary": digest(args.sudachi_small)}
                if args.sudachi_small
                else {}
            ),
        },
        "sizes": sizes,
        "corpusSentences": len(corpus),
        "changedSentences": len(differences),
        "differences": differences,
        "differencesByProvider": differences_by_provider,
        "results": results,
        "learningParity": all(
            x["passed"] for result in results.values() for x in result["learningChecks"]
        ),
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    summary = {
        "learningParity": report["learningParity"],
        "corpusSentences": len(corpus),
        "changedSentences": len(differences),
        "changedSentencesByProvider": {
            name: len(cases) for name, cases in differences_by_provider.items()
        },
        "sizes": sizes,
        "providers": {
            k: {
                field: value
                for field, value in v.items()
                if field not in ("sentences", "learningChecks", "timingSamplesMs")
            }
            | {
                "passedLearningChecks": sum(x["passed"] for x in v["learningChecks"]),
                "totalLearningChecks": len(v["learningChecks"]),
            }
            for k, v in results.items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not all(result["validOffsets"] for result in results.values()):
        raise SystemExit("Original-text offsets were not preserved")
    if args.require_learning_parity and not report["learningParity"]:
        raise SystemExit(
            "Learning parity failed; inspect the reported token/reading differences"
        )


if __name__ == "__main__":
    main()
