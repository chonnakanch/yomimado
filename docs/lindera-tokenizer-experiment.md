# Lindera + IPADIC experiment — 2026-10-17

Branch: `codex/lindera-tokenizer-experiment`, created from `08663d9`.

**Lindera substantially reduces dictionary size, but changes the learning
experience.** This branch adds an explicit development opt-in and a reproducible
comparison. Sudachi Core remains the default; the Lindera option is rejected in
frozen/packaged services. Neither release dependency lock nor runtime seed is
changed, and no installer is built or approved.

## Measured results

The local macOS ARM64 test uses Python 3.11.17, Lindera Python 6.0.0 and its pinned
v6.0.0 IPADIC archive, compared with SudachiPy 0.6.10/Core 20250515 in Split Mode C.
Lindera uses normal mode with no character or token filters, preserving source
text for clicks. The same original-text token API contract is used by both.

| Check                                              | Sudachi Core | Lindera + IPADIC |
| -------------------------------------------------- | ------------ | ---------------- |
| Dictionary directory, regular files                | 207.06 MiB   | 45.33 MiB        |
| Original-text spans over 39 sentences              | Pass         | Pass             |
| Focused word/reading/base-form checks              | 8/8          | 7/8              |
| Sentences with different words/readings/base forms | Baseline     | 20/39            |
| Warm Python adapter median, approximately          | 0.014 ms     | 0.043 ms         |
| Token instances with any JMdict match              | 199/217      | 220/233          |
| Token instances with a matching JMdict reading     | 171/217      | 190/233          |

Dictionary savings are approximately **161.73 MiB** before native package costs.
The local Lindera Python package is about 4.65 MiB. The benchmark also records
the installed Sudachi binding size, which differs from the trimmed frozen bundle.
No final app/installer size has been measured. This experiment does not remove
the separate OCR UniDic dependency.

The warm timing samples cover 25 passes over the corpus (975 calls per adapter).
They measure full Python adapter work, including offset conversion and cached
resource access, not just the underlying engine. Both times are small relative
to image OCR. Initialization timing is a single first call in the benchmark
process, not a controlled cold-start or memory benchmark.

Dictionary-hit counts have different denominators because segmentation changes.
They show the lookup path works; they are not an apples-to-apples accuracy score.
Similarly, 20 changed sentences does not mean 20 errors. Part-of-speech labels
also differ between dictionary schemas and are excluded from that change count.

## Representative behavior differences

| Text                                 | Sudachi Core                      | Lindera + IPADIC                                                           |
| ------------------------------------ | --------------------------------- | -------------------------------------------------------------------------- |
| `お兄ちゃん、待って！`               | `お兄ちゃん` / `オニイチャン`     | `お` + `兄ちゃん` / `ニイチャン`; fails the whole-word compatibility check |
| `食べました。`                       | `食べ` → `食べる`, reading `タベ` | Same base form and reading                                                 |
| `スマートフォン`                     | One word                          | `スマート` + `フォン`                                                      |
| `孫悟空`                             | `孫` + `悟空`                     | One word, reading `ソンゴクウ`                                             |
| `私` in `私は読み窓を使っています。` | `ワタクシ`                        | `ワタシ`                                                                   |
| ASCII `ABC123`                       | Supplies normalized readings      | Unknown ASCII tokens retain their original surface as fallback             |

This is a small diagnostic corpus, not a manga accuracy benchmark. Some
differences may be useful, while others make the current word-selection UI less
convenient. No ad hoc compound-merging rules or user dictionary entries were
added to make the test pass.

## What the branch changes

- [Lindera adapter](../services/ocr/app/tokenizer/lindera.py): checks the exact
  installed version and pinned dictionary file hashes, converts UTF-8 byte
  offsets to code-point offsets, maps IPADIC readings/base forms/POS, and rejects
  mismatched spans or incompatible known-word features.
- [Provider selection](../services/ocr/app/tokenizer/provider.py): uses Sudachi
  by default; enables Lindera only with `YOMIMADO_TOKENIZER=lindera` in development.
  Resource failures become the existing API's explicit service errors.
- [Boundary tests](../services/ocr/tests/test_lindera_tokenization.py): exercise
  emoji/multibyte offsets, inflections, missing features, unknown-word fallbacks,
  corrupt inputs, provider selection and API errors without requiring Lindera in
  normal CI. Cached native calls are serialized to avoid assuming binding-level
  concurrent mutable borrows are safe.
- [Benchmark](../scripts/benchmark_lindera_tokenizer.py): compares both real
  tokenizers and JMdict lookups using only synthetic text and an isolated derived
  word index. It reports quality differences independently of API correctness.

The native wheel and dictionary are in ignored local
`services/ocr/build/lindera-experiment-20261017/`. The experiment manifest records
exact SHA-256 values, and the adapter verifies all ten dictionary files before
loading. The runtime does not download missing resources.

## Try the existing local experiment

Stop the previous Uvicorn service with Ctrl+C first, then run:

```sh
rtk /Users/chonnakan/Projects/yomimado/services/ocr/build/release-venv/bin/python \
  /Users/chonnakan/Projects/yomimado/scripts/dev_lindera_service.py
```

The [development launcher](../scripts/dev_lindera_service.py) resolves paths from
the checkout rather than the terminal's working directory. It configures the
detector code, user-local detector weights, Manga OCR, Lindera, translation and
learning dictionaries using existing local inputs. It checks required OCR paths
before starting, so missing configuration cannot silently start the demo engine.
Explicit existing model/dictionary environment overrides remain supported. Use
`--check` to verify paths without launching, or `--port` to choose another port.
These example absolute paths are for the current local checkout; substitute your
checkout and Python paths when reproducing elsewhere.

Use the normal desktop development launch in another terminal:

```sh
rtk proxy npm --prefix /Users/chonnakan/Projects/yomimado/apps/desktop run tauri -- dev
```

The packaged runtime is not involved. The local service's `GET /health` should
report `{"status":"ok","ocr":"manga"}`. A service launched with only the Lindera
variables reports `"ocr":"demo"` because it lacks `YOMIMADO_DETECTOR_REPO`; the
page scanner rejects that response with **Scanning needs the local OCR models**.
Health identifies the configured engine, not a completed inference test.

Generated dictionary indexes, translation cache and saved test entries use the
experiment's `dev-data/` directory unless explicitly overridden. No installed-app
learning database is replaced. To return to Sudachi, stop this service and use
the usual [development launch with OCR model paths](development.md).

For a fresh checkout, install the hash-pinned optional wheel into an isolated
target, rather than changing the reviewed release environment:

```sh
rtk services/ocr/build/release-venv/bin/python -m pip install \
  --only-binary=:all: --require-hashes --no-deps \
  --target services/ocr/build/lindera-experiment-20261017/site \
  -r services/ocr/requirements-lindera-experiment.txt
```

Obtain `lindera-ipadic-6.0.0.zip` from the exact URL in the
[input manifest](../services/ocr/lindera-experiment-inputs.json), verify SHA-256
`8433dbbb80d7588a565fb9247c1ac7aed3ca50c7463329e495f8bd905aece356`, and extract
its `lindera-ipadic/` directory beneath the local experiment's `dictionary/`.
The adapter validates the extracted files as well. Requirements contain only
the macOS ARM64 and Windows x64 wheel hashes; Python 3.10 or later is required.

## Reproduce the comparison

```sh
rtk env PYTHONPATH="$PWD/services/ocr/build/lindera-experiment-20261017/site" \
  services/ocr/build/release-venv/bin/python scripts/benchmark_lindera_tokenizer.py \
  --dictionary services/ocr/build/lindera-experiment-20261017/dictionary/lindera-ipadic \
  --jmdict apps/desktop/src-tauri/resources/ocr/assets/JMdict_e.gz \
  --output services/ocr/build/lindera-experiment-20261017/benchmark
```

The command is a measurement tool: differing words/readings are recorded rather
than treated as an adapter crash. Add `--require-learning-parity` to enforce the
eight focused learning checks. **That strict mode currently exits nonzero** for
the `お兄ちゃん` check. API/offset failures always fail the run.

The ignored output contains `comparison.json` and a generated
`jmdict-index.sqlite3`. It records versions, source/input hashes, full analyzed
sentences, learning checks, lookup counts and timing samples. User vocabulary and
translation databases are not modified.

## Verification and remaining limits

- All **110 service tests** pass, including 13 new adapter/provider/API cases.
- Four real native-backed ASGI checks preserve the API contract.
- A temporary loopback-only Uvicorn server handles **100 concurrent HTTP requests
  across eight clients** with stable outputs and exact source spans, then stops.
- The corrected development launcher passes three path/configuration tests and
  a separate real HTTP smoke launched from outside the checkout: health reports
  `manga`, both synthetic horizontal/vertical OCR fixtures retain geometry,
  Lindera tokenization and JMdict/KANJIDIC2 lookup pass, and local translation
  returns text. Its ignored evidence is `full-service-smoke.json` and
  `full-service-smoke.log` in the experiment directory. That temporary service
  stops afterward; an existing development service on port 8765 is untouched.
- The frontend typecheck/production build passes. Changed Python lint/format and
  documentation formatting/link checks pass.
- Windows x64 package availability/hashes are recorded, but native Windows,
  PyInstaller/frozen-service integration, interactive popup acceptance and final
  installed size are untested. Rust/native desktop behavior is unchanged by
  this source experiment; no new native app build is claimed.
- The [retained exact notices](../THIRD_PARTY_LICENSES/development/lindera-experiment-2026-10-17/README.md)
  cover the inspected wheel and dictionary input. Full native/transitive source
  delivery and dictionary source identity still require release review.

The branch is ready for development comparison. Switching the release default
would require a deliberate decision about word-selection behavior, broader
Japanese coverage and the existing exact-installer release gates.
