# SudachiPy investigation — 2026-10-17

Historical investigation: the owner subsequently selected Lindera/IPADIC as the
default. See the [migration and adapter contract](lindera-migration.md) for the
current implementation. Results and earlier recommendations below are preserved.

The [expanded candidate comparison](tokenizer-candidate-comparison.md) additionally
tests MeCab/IPADIC, OCR UniDic reuse and two Vaporetto models against this baseline,
using 53 shared sentences and 24 focused learning targets.

**YomiMado already uses SudachiPy 0.6.10 with Sudachi Core 20250515.** It is
the baseline in the Lindera comparison, not another image-recognition model.
Sudachi Small is a smaller dictionary for that same engine. The three-way local
test below makes its tradeoff directly comparable with Lindera/IPADIC.

## Role and implementation

The [application adapter](../services/ocr/app/tokenizer/sudachi.py) caches the
Core dictionary, creates a tokenizer per request, and uses Split Mode C. It
returns source-text offsets, readings, dictionary forms and part-of-speech labels
for selectable study words. It filters symbol-only tokens. JMdict and KANJIDIC2
remain responsible for meanings; comic-text-detector and Manga OCR remain
responsible for image detection and recognition.

Despite its name, the installed SudachiPy 0.6 series is a Python binding to the
Rust engine, not the older pure-Python implementation. Moving calls directly to
Rust would still require its dictionary, and this service still needs Python
for OCR. There is no demonstrated large bundle saving from that move alone.
See the [exact installed version's upstream description](https://pypi.org/project/SudachiPy/0.6.10/)
and [sudachi.rs](https://github.com/WorksApplications/sudachi.rs).

Upstream offers Small (UniDic vocabulary), Core (basic/default vocabulary) and
Full (additional proper nouns). Split modes A/B/C choose shorter/intermediate/
longer word units within a dictionary; changing mode does not remove dictionary
bytes. Full is outside this size-reduction comparison and was not downloaded.
The [dictionary documentation](https://github.com/WorksApplications/SudachiDict)
describes these editions and their separate data terms.

## Same-corpus measurements

Measured on the local macOS ARM64 machine, Python 3.11.17, SudachiPy 0.6.10,
both Sudachi editions 20250515, and Lindera 6.0.0 with its pinned IPADIC archive.
Both Sudachi profiles run the real application adapter in Mode C; the Small
profile substitutes only the dictionary factory within the benchmark process.
No service configuration or installed package is changed.

| Measurement                                 | Sudachi Core | Sudachi Small | Lindera/IPADIC |
| ------------------------------------------- | -----------: | ------------: | -------------: |
| Dictionary payload                          |   207.06 MiB |    117.25 MiB |      45.33 MiB |
| Dictionary saving versus Core               |            — |     89.81 MiB |     161.73 MiB |
| Warm adapter median per sentence            |     0.013 ms |      0.014 ms |       0.043 ms |
| Warm adapter p95 per sentence               |     0.018 ms |      0.020 ms |       0.050 ms |
| Focused word/reading/base-form checks       |          8/8 |           7/8 |            7/8 |
| Sentences differing from Core               |            0 |         10/39 |          20/39 |
| Original-source offsets                     |         Pass |          Pass |           Pass |
| Token instances with any JMdict match       |      199/217 |       218/234 |        220/233 |
| Token instances with a JMdict reading match |      171/217 |       190/234 |        190/233 |

The benchmark uses 39 synthetic sentences and 25 timed passes per profile:
975 calls each, 2,925 total. Times include application token construction and
offset handling, but exclude dictionary lookup and image OCR. Profiles run
sequentially, without controlled background load; microsecond differences are
diagnostic, not a general engine ranking. Small's dictionary factory override
uses a simple function rather than a timed mock object. First-use timings are
recorded but are not controlled cold-start measurements.

Dictionary sizes count regular-file bytes, not compressed installer size or RAM.
The installed binding directories are approximately 7.94 MiB for SudachiPy and
4.65 MiB for Lindera; they are not measured frozen-app costs. All 39 sentences
preserve exact source offsets. Different segmentation changes the number of
tokens, so lookup ratios are not directly comparable accuracy scores. Likewise,
a sentence differing from Core is not necessarily wrong. Eight hand-selected
learning checks do not establish general manga-language accuracy.

## Behavior that matters for word clicks

| Input            | Core                     | Small                             | Lindera                            |
| ---------------- | ------------------------ | --------------------------------- | ---------------------------------- |
| `お兄ちゃん`     | One word, `オニイチャン` | `お / 兄 / ちゃん`; `兄` = `アニ` | `お / 兄ちゃん`, `オ / ニイチャン` |
| `スマートフォン` | One word                 | `スマート / フォン`               | `スマート / フォン`                |
| `東京都`         | One word, `トウキョウト` | `東京 / 都`, `トウキョウ / ト`    | `東京 / 都`, `トウキョウ / ト`     |

Both smaller options fail the existing whole-word `お兄ちゃん` learning check.
Small is closer to Core over this corpus than Lindera, but loses more of this
expression's intended reading. No manual compound merging or custom dictionary
entries were added. The tradeoff affects which words the learner can select and
the lookup query sent to JMdict.

Changing this tokenizer does not change the detector or recognizer. The
[previous scan benchmark](scan-performance-comparison.md) measured identical OCR
outputs for Core and Lindera, with detection accounting for about 88% of OCR
time. Small was not rerun through image scans here, so no Small scan-latency or
image-accuracy measurement is claimed.

## Newer versions

Checked upstream on 2026-10-17: PyPI lists SudachiPy 0.6.11 and 0.7.0 after our
0.6.10 pin. The [upstream changelog](https://github.com/WorksApplications/sudachi.rs/blob/develop/CHANGELOG.md)
describes dependency/PyO3 updates in 0.6.11; this does not establish a size or
accuracy improvement for our workload. Neither newer engine was installed or
benchmarked in this investigation.

SudachiPy 0.7 requires the new V1 dictionary format; our 20250515 V0 dictionary
cannot simply be carried over. Upstream also warns that the 0.7 series is
unstable and may break between patch versions. An engine/dictionary upgrade is
a separate experiment requiring exact matched pins and a fresh language/output
comparison. See the [current package warning](https://pypi.org/project/SudachiPy/)
and [dictionary format compatibility](https://github.com/WorksApplications/SudachiDict#dictionary-format-version).

## Decision

Keep Core as the default for the current learning behavior. Keep Lindera as the
strongest measured dictionary-size candidate, with the documented segmentation
tradeoffs. Small provides an intermediate saving with fewer changed sentences,
but does not preserve all eight learning checks or provide a scan-speed benefit
demonstrated by this test. A broader labeled dialogue/name/reading corpus is
needed to choose a replacement on language quality.

The separate, already tested opportunity to avoid OCR's unused UniDic word
tokenizer is approximately 248.4 MiB and preserves the observed learning output;
see the [resource investigation](tokenizer-resource-investigation.md). That
source experiment still needs frozen-service and platform verification.

## Reproduction and evidence

The existing [benchmark](../scripts/benchmark_lindera_tokenizer.py) now accepts
`--sudachi-small`. It verifies the exact Small dictionary SHA-256 and baseline
SudachiPy version before analysis. Use the previously verified local inputs:

```sh
rtk env PYTHONPATH="$PWD/services/ocr/build/lindera-experiment-20261017/site" \
  services/ocr/build/release-venv/bin/python scripts/benchmark_lindera_tokenizer.py \
  --dictionary services/ocr/build/lindera-experiment-20261017/dictionary/lindera-ipadic \
  --jmdict apps/desktop/src-tauri/resources/ocr/assets/JMdict_e.gz \
  --sudachi-small services/ocr/build/tokenizer-investigation-20261017/sudachi-small-20250515.dic \
  --output services/ocr/build/lindera-experiment-20261017/three-way-benchmark
```

The ignored output retains full tokens, learning checks, pairwise differences,
all timing samples, input/source hashes, versions and an isolated JMdict index.
Add `--require-learning-parity` to make the known failed checks exit nonzero.
The original two-profile invocation remains supported. The exact Small wheel,
dictionary hash, package metadata and license inspection are recorded in the
[earlier investigation](tokenizer-resource-investigation.md#what-changes-with-sudachi-small).
No additional dependencies were downloaded or bundled. Production code, release
locks, model assets, runtime seeds and installer evidence remain unchanged.

Verification passes all 17 existing tokenizer/provider tests, the original
two-profile command, the new three-profile run and mismatched-dictionary
rejection. Strict learning parity correctly exits nonzero for the known checks.
The recorded benchmark hash and all 2,925 timing samples were checked against
their reported medians. Python lint/format and documentation checks pass.
