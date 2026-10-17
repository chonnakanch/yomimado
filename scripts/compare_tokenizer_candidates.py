"""Compare the discussed learning tokenizers using verified, local-only inputs.

Benchmark adapters live here, outside the production provider registry. No OCR
models are loaded and no packages or model files are downloaded by this script.
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
from contextlib import ExitStack, nullcontext
from pathlib import Path
from unittest.mock import patch

from benchmark_lindera_tokenizer import CHECKS, digest, size
from investigate_tokenizer_resources import SUDACHI_TEXTS

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "services/ocr/build/tokenizer-comparison-20261017"
EXTRA_CHECKS = (
    ("聞いた。", "聞い", "キイ", "聞く"),
    ("走って逃げろ！", "走っ", "ハシッ", "走る"),
    ("遊んでいる。", "遊ん", "アソン", "遊ぶ"),
    ("高かった。", "高かっ", "タカカッ", "高い"),
    ("強くなりたい。", "強く", "ツヨク", "強い"),
    ("呼んだ。", "呼ん", "ヨン", "呼ぶ"),
    ("知らない。", "知ら", "シラ", "知る"),
    ("信じてくれ。", "信じ", "シンジ", "信じる"),
    ("帰った。", "帰っ", "カエッ", "帰る"),
    ("友達と約束した。", "友達", "トモダチ", "友達"),
    ("大丈夫だよ。", "大丈夫", "ダイジョウブ", "大丈夫"),
    ("図書館に行こう。", "図書館", "トショカン", "図書館"),
    ("令和の時代。", "令和", "レイワ", "令和"),
    (
        "スマートフォンを買い替えたい。",
        "スマートフォン",
        "スマートフォン",
        "スマートフォン",
    ),
    ("東京都で待ち合わせしよう。", "東京都", "トウキョウト", "東京都"),
    ("孫悟空は強い。", "孫悟空", "ソンゴクウ", "孫悟空"),
)
OFFSET_CASES = (
    "",
    " \t\n",
    "学校 学校\t学校\n学校",
    "🙂学校　 学校で食べました。",
    "ＡＢＣ１２３とABC123。",
    "ｶﾞｯｺｳと学校。",
)


def feature(value: str | None) -> str | None:
    return value if value and value != "*" else None


def make_token(text, surface, start, end, reading, base, pos):
    from app.models import TextToken

    if not surface or text[start:end] != surface or not 0 <= start < end <= len(text):
        raise ValueError("Token does not match its original source span")
    if not any(c.isalnum() for c in surface):
        return None
    return TextToken(
        surface=surface,
        reading=feature(reading) or surface,
        dictionaryForm=feature(base) or surface,
        start=start,
        end=end,
        partOfSpeech=pos,
    )


class MeCabAdapter:
    def __init__(self, tagger, unidic=False):
        self.tagger = tagger
        self.unidic = unidic

    def tokenize(self, text):
        result = []
        cursor = 0
        for node in self.tagger(text):
            gap = node.white_space
            if text[cursor : cursor + len(gap)] != gap:
                raise ValueError("MeCab whitespace does not match the original source")
            cursor += len(gap)
            end = cursor + len(node.surface)
            fields = node.feature
            if self.unidic:
                reading, base = fields.kana, fields.orthBase
                pos = [
                    fields.pos1,
                    fields.pos2,
                    fields.pos3,
                    fields.pos4,
                    fields.cType,
                    fields.cForm,
                ]
            else:
                reading = fields[7] if len(fields) > 7 else None
                base = fields[6] if len(fields) > 6 else None
                pos = fields[:6]
            token = make_token(
                text,
                node.surface,
                cursor,
                end,
                reading,
                base,
                " / ".join(x for x in pos if feature(x)),
            )
            if token is not None:
                result.append(token)
            cursor = end
        if text[cursor:] and not text[cursor:].isspace():
            raise ValueError("MeCab left non-whitespace source text unaccounted for")
        return result


class VaporettoAdapter:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def tokenize(self, text):
        result = []
        for node in self.tokenizer.tokenize(text):
            # The selected two-tag models have POS and kana/pronunciation only.
            # Keep the missing lemma explicit: surface fallback is not stemming.
            token = make_token(
                text,
                node.surface(),
                node.start(),
                node.end(),
                node.tag(1),
                None,
                node.tag(0) or "",
            )
            if token is not None:
                result.append(token)
        return result


def check_targets(sentences, checks):
    results = []
    for text, surface, reading, base in checks:
        # Both are valid dictionary headwords for this inflected form.
        bases = {base, "信ずる"} if base == "信じる" else {base}
        candidates = [x for x in sentences[text] if x["surface"] == surface]
        results.append(
            {
                "text": text,
                "expected": {
                    "surface": surface,
                    "reading": reading,
                    "dictionaryForm": base,
                    "acceptedDictionaryForms": sorted(bases),
                },
                "surface": bool(candidates),
                "surfaceAndReading": any(x["reading"] == reading for x in candidates),
                "surfaceAndBase": any(x["dictionaryForm"] in bases for x in candidates),
                "allFields": any(
                    x["reading"] == reading and x["dictionaryForm"] in bases
                    for x in candidates
                ),
            }
        )
    return results


def signature(tokens):
    return [(x["surface"], x["reading"], x["dictionaryForm"]) for x in tokens]


def validate_tokens(text, tokens):
    previous = 0
    for token in tokens:
        if not previous <= token["start"] < token["end"] <= len(text):
            raise ValueError("Non-monotonic source spans")
        if text[token["start"] : token["end"]] != token["surface"]:
            raise ValueError("Source span mismatch")
        previous = token["end"]


def verify_files(path, expected):
    for relative, sha in expected.items():
        target = path / relative if path.is_dir() else path
        if digest(target) != sha:
            raise ValueError(f"Input hash mismatch: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=EXPERIMENT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=25)
    parser.add_argument("--require-learning-parity", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    manifest_path = ROOT / "services/ocr/tokenizer-comparison-inputs.json"
    manifest = json.loads(manifest_path.read_text())
    for package, version in manifest["versions"].items():
        if importlib.metadata.version(package) != version:
            parser.error(f"Expected {package}=={version}")
    sys.path.insert(0, str(ROOT / "services/ocr"))
    import fugashi
    import lindera
    import sudachidict_core
    import sudachipy
    import unidic_lite
    import vaporetto
    import zstandard
    from app.dictionary.jmdict import lookup
    from app.tokenizer.lindera import LinderaTokenizer
    from app.tokenizer.sudachi import SudachiTokenizer
    from sudachipy import dictionary

    if vaporetto.VAPORETTO_VERSION != "0.6.5":
        parser.error("Expected the compatible Vaporetto 0.6.5 native engine")
    resources = {
        "sudachi-core": Path(sudachidict_core.__file__).parent / "resources",
        "sudachi-small": ROOT
        / "services/ocr/build/tokenizer-investigation-20261017/sudachi-small-20250515.dic",
        "lindera-ipadic": ROOT
        / "services/ocr/build/lindera-experiment-20261017/dictionary/lindera-ipadic",
        "mecab-ipadic": args.experiment / "extracted/ipadic-1.0.0/ipadic/dicdir",
        "mecab-unidic": Path(unidic_lite.DICDIR),
    }
    for variant in ("kana", "pron"):
        name = f"bccwj-suw+unidic_pos+{variant}"
        resources[f"vaporetto-{variant}"] = (
            args.experiment / "extracted" / name / f"{name}.model.zst"
        )
    for name, path in resources.items():
        verify_files(path, manifest["resources"][name]["files"])
    args.output.mkdir(parents=True, exist_ok=True)
    jmdict = ROOT / "apps/desktop/src-tauri/resources/ocr/assets/JMdict_e.gz"
    os.environ.update(
        {
            "YOMIMADO_LINDERA_DICTIONARY": str(resources["lindera-ipadic"]),
            "YOMIMADO_JMDICT": str(jmdict),
            "YOMIMADO_JMDICT_INDEX": str(
                (args.output / "jmdict-index.sqlite3").resolve()
            ),
        }
    )
    legacy_corpus = tuple(dict.fromkeys((*SUDACHI_TEXTS, *(x[0] for x in CHECKS))))
    checks = (*CHECKS, *EXTRA_CHECKS)
    corpus = tuple(dict.fromkeys((*legacy_corpus, *(x[0] for x in EXTRA_CHECKS))))
    with ExitStack() as stack:
        small = dictionary.Dictionary(dict=str(resources["sudachi-small"]))
        stack.callback(small.close)
        ipadic = resources["mecab-ipadic"].resolve()
        unidic = resources["mecab-unidic"].resolve()
        profiles = {
            "sudachi-core": SudachiTokenizer(),
            "sudachi-small": SudachiTokenizer(),
            "lindera-ipadic": LinderaTokenizer(),
            "mecab-ipadic": MeCabAdapter(
                fugashi.GenericTagger(f'-r "{ipadic}/mecabrc" -d "{ipadic}"')
            ),
            "mecab-unidic": MeCabAdapter(
                fugashi.Tagger(f'-r "{unidic}/mecabrc" -d "{unidic}"'), unidic=True
            ),
        }
        decompressed = {}
        for variant in ("kana", "pron"):
            key = f"vaporetto-{variant}"
            with (
                resources[key].open("rb") as source,
                zstandard.ZstdDecompressor().stream_reader(source) as reader,
            ):
                model = reader.read()
            decompressed[key] = {
                "bytes": len(model),
                "sha256": hashlib.sha256(model).hexdigest(),
            }
            profiles[key] = VaporettoAdapter(
                vaporetto.Vaporetto(model, predict_tags=True)
            )

        def context(name):
            return (
                patch("app.tokenizer.sudachi._dictionary", new=lambda: small)
                if name == "sudachi-small"
                else nullcontext()
            )

        results = {}
        timings = {name: [] for name in profiles}
        for name, tokenizer in profiles.items():
            with context(name):
                sentences = {
                    text: [t.model_dump() for t in tokenizer.tokenize(text)]
                    for text in corpus
                }
                offset_outputs = {
                    text: [t.model_dump() for t in tokenizer.tokenize(text)]
                    for text in OFFSET_CASES
                }
            for text, tokens in {**sentences, **offset_outputs}.items():
                validate_tokens(text, tokens)
            results[name] = {
                "sentences": sentences,
                "offsetCases": offset_outputs,
                "legacyChecks": check_targets(sentences, CHECKS),
                "expandedChecks": check_targets(sentences, checks),
                "hasDictionaryForms": not name.startswith("vaporetto"),
                "readingKind": "pronunciation"
                if name == "vaporetto-pron"
                else "orthographic-kana",
            }
        # Alternate profile order after warmup; context setup stays outside each timer.
        names = list(profiles)
        for repeat in range(args.repeats):
            for name in names if repeat % 2 == 0 else reversed(names):
                with context(name):
                    for text in corpus:
                        start = time.perf_counter_ns()
                        profiles[name].tokenize(text)
                        timings[name].append(
                            (time.perf_counter_ns() - start) / 1_000_000
                        )
        for name, result in results.items():
            sentences = result["sentences"]
            words = [token for tokens in sentences.values() for token in tokens]
            hits = [
                lookup(t["surface"], t["dictionaryForm"], t["reading"]) for t in words
            ]
            samples = timings[name]
            result.update(
                {
                    "warmMedianMs": statistics.median(samples),
                    "warmP95Ms": sorted(samples)[int(0.95 * (len(samples) - 1))],
                    "timingSamplesMs": samples,
                    "tokensWithDictionaryMatch": sum(bool(hit) for hit in hits),
                    "tokensWithReadingMatch": sum(
                        any(e.readingMatch for e in hit) for hit in hits
                    ),
                    "tokenCount": len(words),
                    "changedLegacySentences": sum(
                        signature(sentences[t])
                        != signature(results["sudachi-core"]["sentences"][t])
                        for t in legacy_corpus
                    ),
                    "changedSentences": [
                        t
                        for t in corpus
                        if signature(sentences[t])
                        != signature(results["sudachi-core"]["sentences"][t])
                    ],
                    "resourceBytes": size(resources[name])
                    if resources[name].is_dir()
                    else resources[name].stat().st_size,
                    "decompressedModel": decompressed.get(name),
                }
            )

    report = {
        "scope": "local source benchmark; no real-manga, image OCR, frozen-service or Windows claim",
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "versions": manifest["versions"],
        "vaporettoNativeVersion": vaporetto.VAPORETTO_VERSION,
        "sourceHashes": {
            p: digest(ROOT / p)
            for p in [
                "scripts/compare_tokenizer_candidates.py",
                "scripts/benchmark_lindera_tokenizer.py",
                "scripts/investigate_tokenizer_resources.py",
                "services/ocr/app/tokenizer/sudachi.py",
                "services/ocr/app/tokenizer/lindera.py",
                "services/ocr/tokenizer-comparison-inputs.json",
            ]
        },
        "jmdictSha256": digest(jmdict),
        "bindingBytes": {
            "sudachipy": size(Path(sudachipy.__file__).parent),
            "fugashi": size(Path(fugashi.__file__).parent),
            "lindera": size(Path(lindera.__file__).parent),
            "vaporetto": size(Path(vaporetto.__file__).parent),
            "zstandard": size(Path(zstandard.__file__).parent),
        },
        "corpusSentences": len(corpus),
        "legacyCorpusSentences": len(legacy_corpus),
        "expandedTargets": len(checks),
        "offsetCasesPerProfile": len(OFFSET_CASES),
        "results": results,
    }
    (args.output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    for name, result in results.items():
        print(
            json.dumps(
                {
                    "profile": name,
                    "resourceMiB": round(result["resourceBytes"] / 2**20, 3),
                    "rawModelMiB": round(
                        result["decompressedModel"]["bytes"] / 2**20, 3
                    )
                    if result["decompressedModel"]
                    else None,
                    "medianMs": round(result["warmMedianMs"], 6),
                    "p95Ms": round(result["warmP95Ms"], 6),
                    "legacyChecks": sum(x["allFields"] for x in result["legacyChecks"]),
                    "expandedChecks": {
                        field: sum(x[field] for x in result["expandedChecks"])
                        for field in [
                            "surface",
                            "surfaceAndReading",
                            "surfaceAndBase",
                            "allFields",
                        ]
                    },
                    "changedLegacySentences": result["changedLegacySentences"],
                    "hasDictionaryForms": result["hasDictionaryForms"],
                },
                ensure_ascii=False,
            )
        )
    print(
        f"Compared {len(profiles)} profiles, {len(corpus)} sentences, {len(checks)} targets; original spans validated"
    )
    if args.require_learning_parity and not all(
        x["allFields"] for r in results.values() for x in r["expandedChecks"]
    ):
        raise SystemExit("Focused learning checks differ; inspect the recorded cases")


if __name__ == "__main__":
    main()
