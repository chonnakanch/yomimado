# Learning tokenizer candidates versus current Sudachi — 2026-10-17

**Current Sudachi Core remains the best match for the tested learning targets.
Lindera/IPADIC and MeCab/IPADIC offer substantial size reductions with different
word selections. Vaporetto is small and fast but its selected models lack the
base forms needed by the current lookup contract.**

This covers every engine on the earlier replacement shortlist: Lindera/IPADIC,
MeCab/IPADIC through Fugashi, and Vaporetto. It also includes previously tested
Sudachi Small and reusing OCR's existing UniDic Lite through Fugashi. SudachiPy
and sudachi.rs refer to the Python binding and underlying Rust engine already
used by the baseline; they are not two independently measured candidates.
These are learning tokenizers, not image OCR replacements.

## Compared inputs

All profiles were executed locally on macOS ARM64, Python 3.11.17:

- Current baseline: SudachiPy 0.6.10, Sudachi Core 20250515, Split Mode C.
- Sudachi Small: same engine, dictionary date and split mode; only the dictionary
  factory is substituted within the benchmark process.
- Lindera: Python 6.0.0, its pinned v6.0.0 IPADIC archive and the existing opt-in
  application adapter, normal mode without token filters.
- MeCab/IPADIC: existing Fugashi 1.5.2 `GenericTagger`, data extracted from
  `ipadic` 1.0.0. POS, reading and base fields are mapped from IPADIC features.
- MeCab/UniDic: same Fugashi version, existing UniDic Lite 1.0.8. `kana` supplies
  orthographic reading; `orthBase` supplies the original spelling's base form.
- Vaporetto: Python wrapper 0.3.3/native engine 0.6.5, v0.5.0
  `bccwj-suw+unidic_pos+kana` and `bccwj-suw+unidic_pos+pron` models. Both predict
  tags and retain the wrapper's default normalization, which preserves original
  surfaces/offsets on the tested full-width and half-width cases. The model
  format is compatible with this engine; no conversion is performed.

The [manifest](../services/ocr/tokenizer-comparison-inputs.json) pins downloaded
artifacts and every tested dictionary/model file. The [benchmark](../scripts/compare_tokenizer_candidates.py)
checks installed versions and resource hashes before loading. New adapters exist
only in that script; no new production providers or default changes are added.

## Size and warm latency

| Profile                       | Resource files on disk | Median / sentence | p95 / sentence | Dictionary forms |
| ----------------------------- | ---------------------: | ----------------: | -------------: | ---------------- |
| **Sudachi Core — current**    |         **207.06 MiB** |     **0.0126 ms** |  **0.0192 ms** | Yes              |
| Sudachi Small                 |             117.25 MiB |         0.0134 ms |      0.0194 ms | Yes              |
| Lindera/IPADIC                |              45.33 MiB |         0.0405 ms |      0.0506 ms | Yes              |
| MeCab/IPADIC through Fugashi  |              50.48 MiB |         0.0165 ms |      0.0254 ms | Yes              |
| MeCab/UniDic Lite             |             248.40 MiB |         0.0198 ms |      0.0300 ms | Yes              |
| Vaporetto kana + POS          |    5.77 MiB compressed |         0.0100 ms |      0.0151 ms | **No**           |
| Vaporetto pronunciation + POS |    5.75 MiB compressed |         0.0100 ms |      0.0149 ms | **No**           |

Vaporetto's serialized model expands to **55.85/55.84 MiB**, respectively, before
engine construction. Its small on-disk figures use the distributed `.model.zst`
and require a decompressor when loading. These are not RAM/RSS measurements.
The other figures count their regular dictionary files as used locally, not
compressed archive/installer bytes. Binding directories are measured separately:
SudachiPy 7.94 MiB, Lindera 4.65 MiB, Fugashi 1.16 MiB, Vaporetto 1.88 MiB and
zstandard 1.91 MiB. Frozen bundles may trim or collect different files.

Lindera's dictionary advantage over MeCab/IPADIC is about 5.16 MiB, but the
installed bindings narrow their combined resource/binding difference to about
1.67 MiB. That is not a final app-size measurement. All alternatives still need
JMdict/KANJIDIC2 for meanings.

The same 53 synthetic sentences run through every profile, with 25 timed passes:
**1,325 calls each, 9,275 total**. Profiles are warmed, and order alternates by
pass. Timers include conversion to the same application `TextToken` models;
they exclude imports, initialization/decompression, JMdict lookup, HTTP, capture,
OCR and UI rendering. Profiles/resources coexist in one process. Background load
and cold filesystem caches are not controlled, and process memory is not isolated.
This compares these adapters on short texts, not general engine throughput.

## Learning behavior

The first eight targets are unchanged from the previous comparison. Sixteen
additional targets cover inflected verbs/adjectives, common nouns, modern terms
and compounds/names. Each target specifies a desired selectable word, reading
and base form. `信じる` and `信ずる` are both accepted dictionary forms for
the `信じ` target. The test does not require identical POS taxonomies.

| Profile                       | Original targets, all fields | Expanded word + reading targets | Expanded targets, all fields | Changed sentences in original 39 |
| ----------------------------- | ---------------------------: | ------------------------------: | ---------------------------: | -------------------------------: |
| **Sudachi Core — current**    |                      **8/8** |                       **23/24** |                    **23/24** |                                0 |
| Sudachi Small                 |                          7/8 |                           18/24 |                        18/24 |                               10 |
| Lindera/IPADIC                |                          7/8 |                           20/24 |                        20/24 |                               20 |
| MeCab/IPADIC through Fugashi  |                          7/8 |                           20/24 |                        20/24 |                               20 |
| MeCab/UniDic Lite             |                          7/8 |                           19/24 |                        19/24 |                               14 |
| Vaporetto kana + POS          |                          2/8 |                           19/24 |                         5/24 |                               36 |
| Vaporetto pronunciation + POS |                          0/8 |                           14/24 |                         1/24 |                               39 |

These are **focused learning-target checks, not general Japanese accuracy
percentages**. In particular, a preferred compound can be split linguistically
reasonably yet fail a whole-word selection target. The corpus is not a blind
evaluation set, and some cases were selected after earlier observed differences.
Changed sentences need not be errors. The baseline itself misses the desired
whole-word `孫悟空`; both IPADIC profiles supply it, so Core is not declared
universally superior.

Vaporetto's base-form field deliberately falls back to the surface string and is
marked unsupported in the report. Its five kana-model full matches are unchanged
words, not recovered lemmas. `食べ` gets reading `タベ` but no `食べる`; `読ん`
gets `ヨン` but no `読む`. Replacing the current tokenizer would require an
additional lemmatizer/deinflection strategy and new lookup validation. None was
added to improve these scores.

The pronunciation model returns `学校 → ガッコー`, `今日 → キョー`, and
`令和 → レーワ`. These can represent pronunciation correctly while failing the
current dictionary-reading contract (`ガッコウ`, `キョウ`, `レイワ`). The kana
model is therefore the more appropriate Vaporetto profile for this app. No
automatic long-vowel rewriting is used to conceal the difference.

Other useful examples:

- Only Core preserves the complete `お兄ちゃん / オニイチャン` learning target.
  Both IPADIC profiles produce `お / 兄ちゃん`; Small and UniDic Lite produce
  `お / 兄 / ちゃん` with `兄` read as `アニ`.
- Core, UniDic Lite and Vaporetto kana supply the `令和 / レイワ` target. Both
  IPADIC profiles split it into `令 / 和`, with `令` read as `リョウ`. Small
  also splits it, but reads `令` as `レイ`.
- Both IPADIC profiles produce a whole `孫悟空 / ソンゴクウ`. Core splits
  `孫 / 悟空`, but supplies the correct readings for those pieces in this context.
- Core preserves `スマートフォン`, `東京都` and `図書館`; the smaller options
  vary in which compounds they split. Complete tokens are retained in the report.

Every profile passes source-span validation on all 53 sentences and six extra
cases covering empty/whitespace-only strings, repeated words, tabs/newlines,
emoji, full-width ASCII and half-width katakana. Unknown readings/forms retain
the surface as an explicit fallback. This is source-level contract evidence,
not acceptance of new native bindings under concurrent application requests.

## Dictionary lookup diagnostic

All profiles use the same isolated local JMdict index and unchanged application
lookup function. Counts are token instances over the 53 sentences:

| Profile        | Any lookup result | Result with matching reading |
| -------------- | ----------------: | ---------------------------: |
| Core           |           238/257 |                      199/257 |
| Small          |           259/276 |                      220/276 |
| Lindera/IPADIC |           261/274 |                      220/274 |
| MeCab/IPADIC   |           262/275 |                      222/275 |
| MeCab/UniDic   |           258/275 |                      220/275 |
| Vaporetto kana |           226/280 |                      225/280 |
| Vaporetto pron |           226/280 |                      179/280 |

Segmentation changes denominators, shorter tokens can match unrelated entries,
and missing lemmas can lose inflected-word lookup. These ratios are diagnostics,
not correct-definition accuracy. The high reading agreement among Vaporetto
kana's surviving hits does not compensate for its missing base forms.

## Effect on app size and scanning

Reusing the existing UniDic Lite avoids a second morphology dictionary while
OCR still ships that resource. However, keeping its approximately 248.40 MiB
costs more than the current 207.06 MiB Core dictionary alone. The separate
[decode-only OCR experiment](tokenizer-resource-investigation.md) supports
removing UniDic from OCR at source level while retaining Core. Reuse and removal
are competing packaging choices, not cumulative savings. Frozen-service and
Windows ONNX verification are still needed before shipping either strategy.

These learning tokenizers run after recognition when the learner opens a region.
They do not locate text in screenshots. The previous [scan comparison](scan-performance-comparison.md)
found identical detector/recognizer outputs for Core and Lindera, with roughly
88% of measured OCR time in detection. This new comparison performs no image OCR;
it does not claim that the other profiles were tested through screen-to-overlay
scans. Saving a few microseconds here is not a demonstrated scan-speed improvement.

## Recommendation and remaining scope

Keep Core as the default. Lindera and MeCab/IPADIC are the useful size candidates
to carry into a broader labeled manga-dialogue comparison: their complete-field
target results tie here, and their dictionary/binding totals are close. MeCab's
adapter is faster in this local run, but all differences are far below image OCR
latency. Vaporetto kana is worth revisiting if the app adds a separately tested
base-form recovery mechanism. The pronunciation model is a weaker fit for the
current reading contract.

The tested MeCab `ipadic` package intentionally carries an old dictionary; its
[maintainer describes it as a compatibility resource](https://pypi.org/project/ipadic/1.0.0/).
Do not assume Lindera's prebuilt data is byte-identical because both are called
IPADIC; their pinned resources and observed outputs are recorded separately.

Sudachi Full was described as a larger proper-noun edition, not proposed as a
size reduction, and is not installed. Newer SudachiPy 0.6.11/0.7 were discussed as
version research rather than measured replacements; see the
[version investigation](sudachipy-investigation.md#newer-versions). This comparison
does not upgrade them. No native Windows run, frozen integration, concurrency
acceptance, installed/download size, RSS or cold-start benchmark is claimed.

## Reproduce and verify

Use the existing release development environment and previous pinned Lindera/
Small inputs. Obtain the exact new downloads from the manifest and verify their
SHA-256 values. Extract the three data archives under
`services/ocr/build/tokenizer-comparison-20261017/extracted/`, preserving their
directory names. The IPADIC package's `setup.py` is not run. Place the two native
wheels in the experiment directory, then install offline into an isolated target:

```sh
rtk services/ocr/build/release-venv/bin/python -m pip install \
  --no-index --find-links services/ocr/build/tokenizer-comparison-20261017 \
  --only-binary=:all: --require-hashes --no-deps \
  --target services/ocr/build/tokenizer-comparison-20261017/site \
  -r services/ocr/requirements-tokenizer-comparison.txt

rtk env PYTHONPATH="$PWD/services/ocr/build/tokenizer-comparison-20261017/site:$PWD/services/ocr/build/lindera-experiment-20261017/site" \
  services/ocr/build/release-venv/bin/python scripts/compare_tokenizer_candidates.py \
  --output services/ocr/build/tokenizer-comparison-20261017/benchmark
```

The optional requirements are for the exact tested macOS/CPython platform only.
The benchmark downloads nothing, contacts no running service and writes derived
JMdict data only below its output directory. `--experiment` can select another
new-input directory. The report retains complete tokens/checks, resource and
source hashes, versions, differences and all 9,275 timing samples. Its recorded
SHA-256 is `d07a451c373cf3f7fafbf522d5c1bf10b381700ba8ea872cedd55a8e432b8cab`.

Seven new contract/scoring tests cover repeated Unicode words, whitespace,
unconsumed text, invalid byte offsets, missing lemmas, pronunciation differences
and accepted lemma variants. They pass alongside all 17 existing tokenizer tests.
Resources and software/model notices are retained separately in the
[development notice record](../THIRD_PARTY_LICENSES/development/tokenizer-comparison-2026-10-17/README.md).
Production code, release locks, model assets, runtime seeds and installer evidence
are unchanged.

Primary references: [Fugashi dictionary API](https://github.com/polm/fugashi#dictionary-use),
[Vaporetto wrapper/API and compatible engine](https://pypi.org/project/vaporetto/0.3.3/),
[exact distributed model release](https://github.com/daac-tools/vaporetto-models/releases/tag/v0.5.0).
