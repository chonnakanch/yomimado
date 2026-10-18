# Tokenizer resource investigation — 2026-10-17

Historical investigation: the owner subsequently selected Lindera/IPADIC as the
default. See the [migration and adapter contract](lindera-migration.md) for the
current implementation. Results and earlier recommendations below are preserved.

**Recommendation: keep Sudachi Core and pursue removing UniDic Lite from OCR
inference.** An isolated source experiment preserves decoding, synthetic OCR
output and Sudachi analysis without importing UniDic or Fugashi. Switching
Sudachi to Small saves less space and changes the learning UI's word boundaries
and readings, including a common manga expression.

This investigates the implementation at `bf59d18`. Production adapters, frozen
runtimes, model files, dependency locks, packaging recipes and existing installer
evidence are unchanged. No installer is built or approved by this experiment.

## Findings

| Option                                           | Measured size opportunity                                                          | Observed behavior                                                                                        | Recommendation                                                        |
| ------------------------------------------------ | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Remove OCR's UniDic Lite dependency              | About 248.4 MiB of current macOS staged files, before smaller related dependencies | Same 6,144-entry vocabulary, 12,804 decoding cases and 10 synthetic OCR results in an isolated candidate | First implementation candidate; frozen/platform checks still required |
| Replace Sudachi Core with Small, both `20250515` | `system.dic` falls from 207.06 to 117.25 MiB: 89.81 MiB saved                      | Structured tokens differ on 10 of 32 test sentences                                                      | Keep Core as the default                                              |
| Remove Sudachi entirely                          | Would remove its dictionary and binding                                            | Would require a replacement for word spans, readings, base forms and POS                                 | Outside this optimization                                             |

Sizes are regular-file bytes divided by 1,048,576, not compressed installer sizes
or measured final-package savings. The Small input is downloaded into an ignored
experiment directory and read directly; it is not installed into either runtime.

## Why UniDic can be avoided in OCR

The model's tokenizer configuration selects `BertJapaneseTokenizer`, MeCab and
`unidic_lite`, with word tokenization enabled. The installed Manga OCR 0.1.16
recognition path preprocesses an image, generates token IDs, decodes those IDs
and applies text cleanup. It does not encode an input Japanese sentence with the
MeCab word tokenizer. The Windows ONNX recognizer also uses its OCR tokenizer to
decode generated IDs; its separate translation tokenizer does encode text.

In Transformers 4.57.3, the Japanese tokenizer initializes its word tokenizer
only when `do_word_tokenize` is true. ID lookup and decoded-string assembly use
the model vocabulary independently of that word tokenizer. The experiment keeps
the same Japanese tokenizer class, vocabulary, special tokens and cleanup, with
two constructor overrides:

```python
AutoTokenizer.from_pretrained(
    model_path,
    tokenizer_type="bert-japanese",
    local_files_only=True,
    do_word_tokenize=False,
    word_tokenizer_type="basic",
)
```

`word_tokenizer_type="basic"` does not create a basic word tokenizer because word
tokenization is disabled. It avoids a serialization assumption in the pinned
Japanese tokenizer: using only `do_word_tokenize=False` leaves the type as
`mecab`, and `pickle.dumps()` raises `KeyError: 'word_tokenizer'`. The final
two-override candidate passes a serialization round trip and decoding comparison
after restoration, with dictionary imports still blocked.

These settings are suitable for the tested **OCR decode-only use**. They change
input text tokenization behavior and must not be applied to the translation
tokenizer, training, or a general-purpose Japanese text-encoding path. This is
not a proposal to edit the pretrained model files in place.

## What was verified locally

The [reproducible probe](../scripts/investigate_tokenizer_resources.py) launches
the baseline and candidate in separate Python processes. It modifies only the
experiment process's Manga OCR constructor reference, so the actual recognizer
uses the candidate tokenizer without changing installed package code. Candidate
workers reject imports of `unidic_lite`, `unidic`, `fugashi` and `MeCab`.

- Both tokenizers expose exactly the same 6,144 vocabulary entries and IDs.
- **12,804 decoding cases match:** all vocabulary IDs individually, empty and
  special-token sequences, and 256 deterministic mixed sequences up to 300 IDs,
  each with special-token filtering on and off.
- **10 recognition outputs match:** the two checked-in synthetic OCR fixtures,
  plus four newly rendered strings in both horizontal and vertical layouts.
  These include `今日は学校に行きます。`, `無理はダメだよ`, `食べました` and
  `お兄ちゃん！`. No manga screenshots are used.
- Both tokenizers survive serialization and retain decoding behavior on the
  mixed/special-token cases after restoration.
- The real Sudachi application adapter returns identical token surfaces,
  readings, dictionary forms, parts of speech and offsets for eight text cases
  when UniDic imports are blocked. Offsets match the original strings, including
  emoji and punctuation cases.
- All four existing tokenization regression tests pass. The comparison rejects
  changed vocabulary, decoded text, OCR output, Sudachi output, dictionary imports,
  word-tokenizer initialization and failed serialization evidence.

This runs on macOS Apple Silicon with Python 3.11.17, Manga OCR 0.1.16,
Transformers 4.57.3, Torch 2.8.0, Pillow 11.3.0, SudachiPy 0.6.10,
SudachiDict-core 20250515 and UniDic Lite 1.0.8 as the baseline environment.
Inference uses CPU and local model files with offline loading enabled.

The Manga OCR weight SHA-256 is
`c63e0bb5b3ff798c5991de18a8e0956c7ee6d1563aca6729029815eda6f5c2eb`, matching
the existing release pin. The generated comparison records hashes for the
configuration, vocabulary, preprocessing configuration, font and probe script.

## What changes with Sudachi Small

The second experiment loads Small `20250515` directly through the existing
SudachiPy 0.6.10 application adapter, using the same Split Mode C and output
fields as Core. It compares 32 fixed sentences covering ordinary dialogue,
inflections, names, compounds, punctuation and emoji.

Ten sentences produce different structured tokens. Differences are not all
errors: shorter segmentation can be reasonable. However, they change selectable
words, dictionary lookup inputs and sometimes readings. Examples:

| Input                            | Core                                     | Small                                        |
| -------------------------------- | ---------------------------------------- | -------------------------------------------- |
| `お兄ちゃん、待って！`           | `お兄ちゃん` with reading `オニイチャン` | `お / 兄 / ちゃん`, with `兄` read as `アニ` |
| `東京都で待ち合わせしよう。`     | `東京都`                                 | `東京 / 都`                                  |
| `スマートフォンを買い替えたい。` | `スマートフォン`                         | `スマート / フォン`                          |
| `東京スカイツリーに行った。`     | `東京スカイツリー`                       | `東京 / スカイ / ツリー`                     |

The `お兄ちゃん` case is a concrete reason to retain Core for the current manga
learning UI. The corpus is a small diagnostic, not a representative quality
benchmark or proof that Core handles every character name correctly.

The exact Small wheel is
`sudachidict_small-20250515-py3-none-any.whl` (41,766,141 download bytes), verified
against PyPI SHA-256
`5b59539c8c149a274e66d926b3f8a1baabe0c2e3715135f296ad28f5bfdc4cb8`.
Its extracted dictionary is 122,948,263 bytes, SHA-256
`2cc37253779a4668815c9c2c019057de8f698675fb57d85ddd7731ab3f6d90b3`.
The packaged Core dictionary is 217,116,143 bytes. Wheel licence metadata and its
Apache-2.0 text were inspected; this experiment is not a release source/asset
approval. Any future bundled replacement still needs full data/source review.

Upstream documents Small as UniDic vocabulary and Core as the basic/default
edition. A shared vocabulary origin does not make MeCab and Sudachi binary
dictionaries interchangeable. Keep engine and dictionary versions paired:
upstream also documents a new dictionary format incompatible with older engines.
The experiment deliberately uses `20250515`, matching the current Core version.
See [SudachiDict](https://github.com/WorksApplications/SudachiDict) and the
[exact Small package](https://pypi.org/project/sudachidict-small/20250515/).

## Reproduce

From the repository root, using the existing reviewed development/release Python
environment and local model assets:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/investigate_tokenizer_resources.py \
  --model apps/desktop/src-tauri/resources/ocr/assets/manga-ocr-base \
  --font '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc' \
  --output services/ocr/build/tokenizer-investigation-20261017
```

To include the Small comparison, provide the extracted, hash-verified same-version
dictionary with
`--sudachi-small services/ocr/build/tokenizer-investigation-20261017/sudachi-small-20250515.dic`.
The probe itself downloads and installs nothing. For another platform, supply a
local Japanese font and compatible pinned Python environment; equivalent native
Windows execution has not been performed here.

Ignored local evidence is retained in
`services/ocr/build/tokenizer-investigation-20261017/`: worker JSON/logs,
`comparison.json`, the exact Small wheel, its PyPI metadata and extracted
dictionary. Reports contain synthetic text, input hashes and platform/version
identities; no font files, model weights or screenshots are added to Git.

## Before implementing the package reduction

1. Add an explicit OCR-only tokenizer construction path on macOS and the Windows
   ONNX adapter, retaining the model's vocabulary and exact decoding behavior.
2. Remove explicit UniDic collection from the two freeze recipes and prevent
   transitive imports from pulling UniDic/Fugashi back in. Keep translation's
   text-encoding tokenizer and Sudachi Core unchanged.
3. Verify inference in frozen services without those modules/files available,
   including startup/warmup, restart and the Windows CPU ONNX path. The current
   experiment covers source-level Torch recognition, not actual Windows ONNX
   execution or either frozen service.
4. Run existing full OCR geometry/API, tokenization, dictionary and translation
   checks. Broaden private/synthetic recognition coverage and record startup,
   memory and actual installed/download size; no latency or memory saving is
   claimed by this probe.
5. Update exact dependency inventories, sources/notices and the reviewed macOS
   runtime seed through the [release process](desktop-release.md). New installers
   need their own exact-hash acceptance and separate owner publication approval.

The app's two dictionaries for meanings remain separate resources; this result
does not require consolidating or removing JMdict/KANJIDIC2. See
[the resource-flow guide](app-resources.md) for their roles.
