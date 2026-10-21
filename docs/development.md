# Development

Run commands below from the repository root unless a `cd` is shown. The desktop
requires Node.js, npm, Rust, and Tauri platform prerequisites. The development
OCR service requires Python 3.10 or later; release builders use their pinned
interpreters and dependencies.

See [project structure](architecture.md#repository-map) for source responsibilities and local
API examples, and [the reading guide](usage.md) for the app controls.

Follow [Git conventions](git-conventions.md) for branches, commits, PRs and merges.

## Start the app

This guide is for a source checkout. Start both the local service and desktop
host; `tauri dev` does not start the service. The minimal configuration returns
a labeled demo boundary until OCR models are configured. Settings may say
**Managed by the development OCR service**; that status does not prove the
service can recognize text. For an installed app, use the
[installation guide](installation-guide.md) instead.

The source and packaging recipes use Lindera/IPADIC for learning analysis.
See [architecture](architecture.md#ocr-decoding-and-learning-tokenization) for
the tokenizer and OCR boundaries.

Start the OCR service in one terminal (Python 3.10+):

```sh
cd services/ocr
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,tokenization]'
python ../../scripts/prepare_lindera.py --download
uvicorn app.main:app --reload --port 8765
```

Start the desktop app in another terminal:

```sh
cd apps/desktop
npm ci
npm run tauri dev
```

To inspect the exact PNG sent to OCR and every returned text region before
showing the overlay, start the desktop app with capture debug mode enabled:

```sh
cd apps/desktop
rtk proxy env VITE_CAPTURE_DEBUG=1 npm run tauri -- dev --no-watch
```

After capture, the debug preview holds the in-memory image and OCR regions.
Expand **Geometry** or **Detector stage** to inspect polygons, crops, recognition
and filter/retry reasons. Choose **Show overlay** to continue or **Close** to cancel.
Hover tooltips also require this flag; ordinary reading keeps accessible labels
and review cues without them. Restart the desktop app after changing the flag.
On Windows PowerShell, set `$env:VITE_CAPTURE_DEBUG="1"` before `npm run tauri dev`.

For pipeline behavior and recovery rules, see [architecture](architecture.md) and
[OCR accuracy scope](implementation-plan.md#small-text-and-vertical-ocr-accuracy).
Use [UI testing](ui-testing.md#native-overlay-checks) for native geometry/input checks.

macOS requires Screen Recording permission. If macOS prompts during the first
capture, enable YomiMado in **System Settings → Privacy & Security → Screen &
System Audio Recording**, then restart the app. When running `tauri dev`, macOS
may list the terminal application instead. A bare command-launched executable
may have no macOS bundle identifier, so an external utility's bundle-based
exception may not cover it. Without this permission, macOS can
return a screenshot containing only the desktop background instead of the
visible windows. The placeholder OCR endpoint does not download models or send
images over the network.

### Windows PowerShell

Use the same Python extras, with Windows virtual-environment activation:

```powershell
cd services/ocr
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e '.[dev,tokenization]'
python ../../scripts/prepare_lindera.py --download
uvicorn app.main:app --reload --port 8765
```

In another terminal, run `npm ci` and `npm run tauri dev` from `apps/desktop`.
Set model and dictionary paths with `$env:NAME="C:\absolute\path"` before
starting the service.

## Local OCR models (development mode)

The service supports a user-local checkout of
[comic-text-detector](https://github.com/dmMaze/comic-text-detector) and a local
[Manga OCR](https://github.com/kha-white/manga-ocr) model directory. These are
not bundled or downloaded in development mode. Install the detector checkout's own
requirements and then install `manga-ocr==0.1.16` with
`pip install -e '.[ocr]'` from `services/ocr`. Set these paths before starting
Uvicorn:

```sh
export YOMIMADO_DETECTOR_REPO=/absolute/path/to/comic-text-detector
export YOMIMADO_DETECTOR_MODEL=/absolute/path/to/comictextdetector.pt.onnx
export YOMIMADO_MANGA_OCR_MODEL=/absolute/path/to/manga-ocr-base
```

The first request loads both models and may take time. The detector supplies
geometry and orientation; Manga OCR recognizes each detected crop. The model
API does not provide a calibrated recognition confidence, so the response uses
`0` to indicate that confidence is unknown. Keep the checkout and weights
outside this repository until their distribution terms are reviewed.

## Local translation model (optional)

Run the development service before opening **Settings → Reading**. Install the
translation extra for local Marian inference, or run Ollama separately. Select
and activate the provider through the settings UI; setting a model environment
path alone does not activate API translation. Supported formats and user controls
are in [translation model setup](translation-model-selection.md).

For an existing local resource tree, `scripts/dev_lindera_service.py --check`
validates paths; running the launcher without `--check` starts the service with
its configured OCR/dictionary resources. Use your prepared service environment.

Install the optional Python dependencies in the OCR service environment and
download the model to the git-ignored local model directory:

```sh
cd services/ocr
pip install -e '.[dev,translation]'
hf download Helsinki-NLP/opus-mt-ja-en --local-dir ./local-models/opus-mt-ja-en
uvicorn app.main:app --reload --port 8765
```

Choose **Import local model** in Settings and import the downloaded folder. In a
browser-only development preview, enter its full path instead of using the native
folder picker. For the service URL, request guards, API examples and payload
limits, see [local service usage](architecture.md#local-service-usage). Translation
cache defaults to `~/.cache/yomimado/translation.sqlite3`; override it with
`YOMIMADO_TRANSLATION_CACHE`.

## Japanese tokenization

The `tokenization` Python extra installs pinned Lindera 6.0.0. The explicit
`prepare_lindera.py --download` setup command stages its hash-verified IPADIC
dictionary under `services/ocr/local-dictionaries/lindera-ipadic`. Supply a local
archive with `--archive /absolute/path/lindera-ipadic-6.0.0.zip` for offline setup.
The running app never downloads this resource. Override the directory with
`YOMIMADO_LINDERA_DICTIONARY` if needed; arbitrary dictionary versions are rejected.
Token analysis is independent of translation. Source-offset and reading contracts
are defined in [architecture](architecture.md#ocr-decoding-and-learning-tokenization).
Without the extra, OCR remains available and learning analysis reports setup guidance.

For historical comparisons only, install `.[tokenization-baseline]` and select
`YOMIMADO_TOKENIZER=sudachi` in a source service. Packaged services require Lindera
and exclude Sudachi. OCR uses decode-only tokenization; it does not require the
learning dictionary or OCR word-segmentation dictionaries.

## Local word dictionary

JLPT vocabulary labels are a separate frontend data asset, not a JMdict field.
The retained Waller/Kraus snapshot, terms and hashes are documented in the
[data review](../THIRD_PARTY_LICENSES/jlpt/README.md). Run
`rtk python3 scripts/prepare_jlpt.py --check` from the repository root to verify
the bundled table and license offline. Omit `--check` to regenerate them from
the retained inputs. Levels use exact spelling/reading matches. The full license
is embedded in the frontend independently of the OCR runtime's notice directory.

For combined-word meanings (for example, 今日 → “today” rather than the
separate meanings of 今 and 日), download the English-only
[JMdict_e.gz file from EDRDG](https://www.edrdg.org/pub/Nihongo/JMdict_e.gz)
to `services/ocr/local-dictionaries/JMdict_e.gz`. This directory is
git-ignored. Alternatively, set `YOMIMADO_JMDICT` to an absolute path to the
compressed `.gz` or uncompressed XML file before starting the OCR service.
The service creates a local SQLite lookup index on first use in the same
directory; set `YOMIMADO_JMDICT_INDEX` to an absolute writable path if needed.
It rebuilds the index when the source file changes. Refresh your local copy
regularly from EDRDG; YomiMado does not download or silently update it.

Saved words and sentences are stored separately from disposable captures/cache in
`~/Library/Application Support/YomiMado/vocabulary.sqlite3` on macOS or
`%APPDATA%\YomiMado\vocabulary.sqlite3` on Windows. Override this with
`YOMIMADO_VOCAB_DB` before starting the OCR service. Saved-data behavior is described in [usage](usage.md#saved-words-and-sentences).

JMdict is copyright the Electronic Dictionary Research and Development Group,
provided under [CC BY-SA 4.0 and the EDRDG dictionary licence](https://www.edrdg.org/edrdg/licence.html).

## Local kanji dictionary

For kanji meanings and readings, download the current
[KANJIDIC2 XML file](https://www.edrdg.org/kanjidic/kanjidic2.xml.gz)
from the [EDRDG KANJIDIC project](https://www.edrdg.org/wiki/KANJIDIC_Project.html)
to `services/ocr/local-dictionaries/kanjidic2.xml.gz` (this directory is
git-ignored). Alternatively, set `YOMIMADO_KANJIDIC2` to the absolute path of
an uncompressed `.xml` or compressed `.xml.gz` copy before starting the OCR
service. Restart the service after replacing the file. Refresh this local copy
regularly from EDRDG; YomiMado does not download or silently update it.

JMdict is required for example compounds; KANJIDIC2 character lookup can work
independently. See [architecture](architecture.md#where-the-displayed-readings-and-meanings-come-from)
for dictionary roles and [usage](usage.md#learning-popup) for the learning controls.

KANJIDIC2 is copyright the Electronic Dictionary Research and Development
Group, provided under [CC BY-SA 4.0 and the EDRDG dictionary licence](https://www.edrdg.org/edrdg/licence.html).

## Local checks

Use the existing development environments from setup above. Frontend checks run
from `apps/desktop`:

```sh
npm run format:check
npm run typecheck
npm test
npm run build
```

`npm run dev` starts only the browser UI; `npm run tauri dev` starts the native
desktop host as well. Capture, shortcuts, tray menus and native overlays require
the desktop host. `npm run build` checks TypeScript and builds frontend assets;
it does not create an installer.

With the Python service environment active, run from `services/ocr`:

```sh
python -m ruff check app tests packaged_main.py windows_packaged_main.py windows_onnx_backend.py
python -m ruff format --check app tests packaged_main.py windows_packaged_main.py windows_onnx_backend.py
python -m pytest -q tests
```

The tokenizer tests require the prepared IPADIC resource. Optional inference or
image dependencies affect which tests can run in a minimal development environment;
the CI setup below provides the complete model-free regression environment.

For native changes, run from the repository root on macOS or Windows using the
Rust version pinned by CI:

```sh
cargo +1.98.1 fmt --manifest-path apps/desktop/src-tauri/Cargo.toml --all --check
cargo +1.98.1 clippy --locked --all-targets --manifest-path apps/desktop/src-tauri/Cargo.toml -- -D warnings
cargo +1.98.1 test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo +1.98.1 build --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
```

These commands require the Tauri platform build prerequisites. They verify source
and debug compilation; exact installer acceptance remains a separate release gate.
For release-tool changes, follow the matching suites in
[Checks](../.github/workflows/checks.yml) and [script roles](../scripts/README.md).

## Required CI checks

[Checks](../.github/workflows/checks.yml) runs frontend formatting/type/tests/build,
service and release-tool regressions, and native formatting/tests/Clippy/debug
builds on macOS and Windows. Its required `gates` job accepts only successful
results from every job/matrix entry. See [Git conventions](git-conventions.md)
for triggers and merge requirements, and the [release runbook](release-runbook.md)
for installer workflows.

Active workflows: [Checks](../.github/workflows/checks.yml) verifies main pushes
and main-targeted PRs; [Release](../.github/workflows/release.yml) builds a merged
release topic in trusted main context. The
[runbook](release-runbook.md#trusted-merge-context-and-publication-recovery) owns
execution and publication details. Both workflow files are included in
release-tool CI. Version consistency and release-tool regression tests stay in
required PR/main Checks; actual frozen-seed compatibility is enforced only by
[Release](release-runbook.md#dynamic-reviewed-seed-selection), before installers
build. An unfinished replacement seed does not block feature integration. The temporary v0.5.0 recovery workflow was retired after
[successful publication](release-recovery-0.5.0.md#completed-recovery-and-retirement).

Service CI uses Python 3.11.17 and
[requirements-ci.txt](../scripts/requirements-ci.txt), with exact wheel hashes
and all image/tokenizer dependencies installed. It runs service tests alongside
the model-free decoder-cache, scan-accuracy and benchmark-comparison contracts,
using pytest so both unittest classes and pytest functions are collected. It
rejects skipped tests across this combined suite. The tests use synthetic data
and fake inference sessions; CI does not install Torch or inference models.
CI explicitly prepares the pinned IPADIC dictionary before testing.
The lock supports Ubuntu x64 CI and local macOS Apple Silicon verification;
Linux is a test runner, not a supported desktop distribution. Dependency/source
refresh and installed-runtime verification remain separate release work.

Jobs run in parallel and cache npm/pip downloads and native compilation. New
commits cancel outdated Checks runs for the same ref; release publisher
concurrency is separate.

## Packaged builds

Use the [release runbook](release-runbook.md) and platform build/verification
records linked from the [desktop checklist](desktop-release.md). Packaged runtime
inputs are reviewed separately from development extras.

Runtime ports, resource paths, generated files and user data locations are
explained in [architecture](architecture.md#generated-and-user-local-files).
Detector import and first launch belong in the
[installation guide](installation-guide.md); dictionary refresh belongs in the
[dictionary update procedure](dictionary-updates.md).
