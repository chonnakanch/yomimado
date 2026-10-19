# Lindera/IPADIC migration — 2026-10-18

At the owner's request, Lindera 6.0.0 with the pinned IPADIC resource replaces
Sudachi Core for word analysis in the source app and both packaging recipes.
This changes the default provider and release inputs. It does not publish an
installer or transfer prior installer acceptance to the changed runtime.

## Behavior and size

Lindera supplies word spans, katakana readings, dictionary forms and parts of
speech through the existing `TextToken` contract. UTF-8 byte offsets are converted
to Unicode code-point offsets and validated against the original string, including
non-BMP characters. Calls to the cached native tokenizer are serialized. Unknown
words keep their original surface when a reading or base form is unavailable.
JMdict meanings and KANJIDIC2 information remain separate local resources.

The [seven-profile comparison](tokenizer-candidate-comparison.md) measured the
dictionary at **45.33 MiB**, versus **207.06 MiB** for Sudachi Core: **161.73 MiB
less dictionary data**, before native binding costs. This is not an installer
download-size measurement. Lindera met 20/24 focused learning targets versus
Core's 23/24; for example, `お兄ちゃん` is split into `お` and `兄ちゃん`.
The owner selected this size/segmentation tradeoff. These checks are a small
curated corpus, not a general accuracy estimate.

Detection, recognition models, geometry and OCR's UniDic/Fugashi initialization
remain unchanged. Tokenizer choice does not make text detection faster or more
accurate; see the separate [scan comparison](scan-performance-comparison.md).

## Port and adapters

The learning API depends on the `JapaneseTokenizer` protocol in
[`app/tokenizer/__init__.py`](../services/ocr/app/tokenizer/__init__.py).
Its single method is `tokenize(text: str) -> list[TextToken]`. Native package
objects and dictionary schemas stay inside the adapters:

```text
React learning popup
  → POST /api/v1/tokenize
  → JapaneseTokenizer port
      → LinderaTokenizer adapter (default)
      → SudachiTokenizer adapter (source comparison)
```

[`provider.py`](../services/ocr/app/tokenizer/provider.py) is the composition
point: it reads `YOMIMADO_TOKENIZER` and imports only the selected adapter.
The API injects that port through `resolve_tokenizer`; tests or an embedded
service can override the dependency without importing native packages.
Adapter failures become explicit HTTP 503 setup errors; there is no silent
fallback to a different engine.

To add another engine, implement the port, map its output into the existing
`TextToken` fields and add its selection at the composition point. Preserve
original Unicode spans, readings, base forms and unknown-word behavior. Pin its
dependencies/data, retain licences, and verify its adapter and packaged resources.
The API, React UI, JMdict lookup and kanji code need no engine-specific changes.
An installed app can select only an adapter whose dependencies/resources were
included in that build; carrying every engine would undo the size saving.

This port covers word analysis. Detection and image recognition remain separate
OCR concerns behind their existing service API; replacing a geometry-producing
detector requires preserving polygons, orientation and coordinate semantics too.

## Resource preparation and packaging

Install `services/ocr` with its `tokenization` extra, then run from the repo root:

```sh
python scripts/prepare_lindera.py --download
```

For offline preparation, replace `--download` with
`--archive /absolute/path/lindera-ipadic-6.0.0.zip`. `--check` verifies staged data.
The default development directory is
`services/ocr/local-dictionaries/lindera-ipadic`; an absolute
`YOMIMADO_LINDERA_DICTIONARY` overrides it. Runtime never downloads a dictionary.
See [development setup](development.md) for the separate OCR model paths.

Both native launchers select Lindera and `assets/lindera-ipadic`. A frozen service
can also resolve that sibling resource without environment overrides. The
[runtime manifest](../services/ocr/app/tokenizer/lindera-inputs.json) pins the
native version, dictionary archive, all ten extracted files and notices.
Preparation rejects changed or unexpected data and never overwrites a modified
existing dictionary. The manifest is included as Python package data and copied
into frozen resources and notices.

macOS and Windows dependency locks replace SudachiPy/Core with Lindera. Freezing
collects Lindera and excludes Sudachi; resource verifiers check dictionary hashes,
runtime pins, retained licences and accidental Sudachi remnants. MIT software and
NAIST/ICOT data terms are retained separately under
[third-party notices](../THIRD_PARTY_LICENSES/lindera/README.md).
Source collectors retain the exact tagged monorepo and locked Rust sources.

The Sudachi adapter and `tokenization-baseline` extra remain only for explicit
source comparisons using `YOMIMADO_TOKENIZER=sudachi`. A frozen app rejects that
selection. Historical experiments and v0.1.0 hashes remain unchanged.

## Verification and release limits

- All 113 service tests pass with the real Lindera binding and pinned dictionary,
  including an injected engine-independent adapter and its failure boundary.
- All 256 release-tool tests pass, including safe dictionary staging and rejection
  of retained Sudachi resources; Rust tests and frontend production build pass.
- A fresh private PyInstaller macOS service passes real HTTP checks for the
  default tokenizer without tokenizer/dictionary overrides, non-BMP spans,
  inflection, 100 concurrent analysis requests, horizontal/vertical OCR geometry,
  JMdict, KANJIDIC2 and local translation.

Private frozen evidence is retained locally under
`services/ocr/build/lindera-production-20261017/` (`frozen-smoke.json` and log,
with executable and runtime-pin hashes). The build used the existing reviewed
development runtime plus the pinned native Lindera wheel. Two unused Sudachi
metadata directories copied by a Transformers hook were removed from this private
build; the resulting bundle passed the new resource verifier. A clean release
lock does not install those packages. This is service integration evidence, not
an exact installer or a newly approved runtime seed.

Native Windows freezing/execution and exact installers have not been tested in
this migration. The macOS runtime seed dependency guard remains enforced: these
new dependencies require a newly reviewed seed. Complete native source/notice
review, dictionary source provenance, fresh candidate hashes and platform
acceptance before publishing. The old release approvals do not cover this change.
