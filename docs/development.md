# Development

Run commands below from the repository root unless a `cd` is shown. The desktop
requires Node.js, npm, Rust, and Tauri platform prerequisites. The development
OCR service requires Python 3.10 or later; release builders use their pinned
interpreters and dependencies.

See [project structure](project-structure.md) for source responsibilities and local
API examples, and [the reading guide](usage.md) for the app controls.

## Start the app

The source and packaging recipes use Lindera/IPADIC for learning analysis.
See the [migration report](lindera-migration.md) for measured differences from
Sudachi and the remaining release checks. Published v0.1.0 evidence is historical.

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

After selecting a region or scanning a page, the debug view shows the captured
image and recognized text using the shared design-system surfaces and controls.
Orange marks final regions; dashed orange marks review/approximate geometry.
Thin cyan dashes identify detector candidates; muted dots identify filtered boxes.
Expand **Geometry** or **Detector stage** for coordinates, individual crops,
recognitions and filter reasons. Medium and large captures receive a bounded retry on
overlapping image tiles; duplicate boxes are merged, and the detector list
labels tile results.
Exactly uniform RGB captures and retry tiles skip model inference; any pixel
variation retains the existing detection path. Debug retry counts reflect the
nonuniform tiles attempted. Identical crop bounds can reuse recognition within
one scan; results are never reused across captures. See the
[retry/crop optimization measurements](detector-retry-optimization.md).
Gray boxes were filtered; their reasons appear in the detector list. The first
filter only removes nearly uniform crops and recognized text
without Japanese characters. It does not reliably distinguish manga artwork
from text when OCR hallucinates Japanese. Captures are held in memory, not saved
as PNG files. On the first launch after this change, YomiMado removes its older
`capture-<number>.png` files from its own captures cache. For a small selection
with one incomplete or missing detector region, the service also tries Manga OCR
on the whole selected crop. If it recovers plausible text, the overlay uses a
dashed, approximate selection-area box rather than claiming precise text
geometry. Choose **Show overlay** to continue or **Close** to cancel. Hover tooltips
on OCR boxes, toolbar buttons and the popup's Check OCR indicator also require this
flag; accessible labels and review details remain available in normal mode.
This flag is read when Vite
starts; restart both the desktop app and OCR service after updating them, and
restart the desktop app without the flag to return to the normal flow. On Windows
PowerShell, set `$env:VITE_CAPTURE_DEBUG="1"` before running `npm run tauri dev`.

macOS requires Screen Recording permission. If macOS prompts during the first
capture, enable YomiMado in **System Settings → Privacy & Security → Screen &
System Audio Recording**, then restart the app. When running `tauri dev`, macOS
may list the terminal application instead. Without this permission, macOS can
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

If Settings → Reading cannot connect to the local service, ensure the separate
development service is running on port 8765. `npm run tauri dev` does not start
that service. With the existing local experiment environment and resources, run
`services/ocr/build/release-venv/bin/python scripts/dev_lindera_service.py` from
the repository root in another terminal, then choose **Try again** in Settings.
The launcher validates local OCR paths; it does not download or automatically
activate a translation model. Installed release apps start their bundled service
automatically.

Translation weights are omitted from the installer. **Settings → Reading →
Local translation** offers **Import local model** and **Ollama**. A fresh setup
has no active translator. Import a compatible Marian folder or install/select a
local model through Ollama. The old built-in/default model option is removed;
`YOMIMADO_TRANSLATION_MODEL` alone no longer activates translation through the API.
See [model selection and platform formats](translation-model-selection.md).

The on-demand popup can translate Japanese text to English with the free,
user-installed [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en)
model. This is a baseline model, not a manga-specific or contextual translator.
Neither model weights nor Japanese text are sent to a cloud translation service
at runtime. Ollama model downloads start only on an explicit user click.

Install the optional Python dependencies in the OCR service environment and
download the model to the git-ignored local model directory:

```sh
cd services/ocr
pip install -e '.[dev,translation]'
hf download Helsinki-NLP/opus-mt-ja-en --local-dir ./local-models/opus-mt-ja-en
uvicorn app.main:app --reload --port 8765
```

Choose **Import local model** in Settings and import that downloaded folder.
Alternatively, run Ollama locally and use its model selection/download controls.
The popup reports a setup error until a model is explicitly installed and
selected. Successful translations are cached locally in
`~/.cache/yomimado/translation.sqlite3` (override with
`YOMIMADO_TRANSLATION_CACHE`). Only the selected Japanese text is sent from
the desktop window to this loopback service; screenshots are not submitted for
translation. The service rejects non-loopback Host headers and untrusted browser
origins. All `/api/` requests require `X-YomiMado-Client: desktop`, which the
frontend and packaged smoke clients send automatically. This forces browser
preflight for uploads and saved-data access; it is not a secret or authentication
against other local processes. Manual API clients must send this header too.

Requests are capped before JSON/multipart parsing: 32 MiB for the complete OCR
upload including multipart overhead, and 1 MiB for other requests. PNG captures
are limited to 40 million pixels and 16,384 pixels per side before decoding or
model loading. If a capture exceeds these limits, select a smaller area. Full
Retina and 8K dimensions fit the pixel limits, although a poorly compressing PNG
can still exceed the upload byte limit.

## Japanese tokenization

The `tokenization` Python extra installs pinned Lindera 6.0.0. The explicit
`prepare_lindera.py --download` setup command stages its hash-verified IPADIC
dictionary under `services/ocr/local-dictionaries/lindera-ipadic`. Supply a local
archive with `--archive /absolute/path/lindera-ipadic-6.0.0.zip` for offline setup.
The running app never downloads this resource. Override the directory with
`YOMIMADO_LINDERA_DICTIONARY` if needed; arbitrary dictionary versions are rejected.
Analysis works without a translation model or network service.
The selected OCR string is sent to the local
`POST /api/v1/tokenize` endpoint when its popup opens; edited text is analyzed
again only when **Analyze words** is pressed. The endpoint preserves the exact
input and returns Unicode code-point offsets for word tokens. It omits
punctuation-only and symbol-only study tokens, while keeping punctuation in the
source sentence for translation. Readings are returned in IPADIC's katakana
form. The popup offers precise word selection in the OCR text, not directly on
the manga image; the detector currently provides region polygons, not
per-character positions. If the extra is not installed, OCR and translation
continue to work and the popup shows a tokenization setup error.

For historical comparisons only, install `.[tokenization-baseline]` and select
`YOMIMADO_TOKENIZER=sudachi` in a source service. Packaged services require Lindera
and exclude Sudachi. Manga OCR's UniDic setup is separate and remains unchanged.

## Local word dictionary

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

Selecting a word in the popup requests its possible JMdict senses from the
local OCR service. Inflected words also try their Lindera dictionary form.
Multiple senses are shown because this lookup does not choose a meaning from
sentence context. The separate **Translate locally** action remains optional.
If JMdict is missing, the popup shows the expected setup path and other
learning features continue to work.

Saved words and sentences are stored separately from disposable captures/cache in
`~/Library/Application Support/YomiMado/vocabulary.sqlite3` on macOS or
`%APPDATA%\YomiMado\vocabulary.sqlite3` on Windows. Override this with
`YOMIMADO_VOCAB_DB` before starting the OCR service. A saved word contains
the chosen dictionary entry's possible meanings and its Japanese source text.
A separately saved sentence contains Japanese text and, optionally, a
translation the reader already requested. Neither record contains a screenshot
or an automatically generated translation. Re-saving the same word/context or
sentence updates its record without creating a duplicate. Restart the OCR
service after updating to a version with this API.

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

The popup requests a single kanji only when clicked. Lookup stays on the local
OCR service; neither manga images nor selected text are sent to EDRDG. If the
file is missing, the popup shows the setup path rather than inventing a meaning.
This initial slice shows character meanings/readings and the word where the
character appeared. When a kanji is clicked, YomiMado also shows up to three
short JMdict compound words containing that character, preferring common
entries. Each shows a reading and English meanings. These are dictionary
examples, not usage sentences or
claims about the character's reading in the selected manga word. If JMdict is
missing, kanji meanings from KANJIDIC2 remain available.

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

[Checks](../.github/workflows/checks.yml) runs on develop/main pushes and main
pull requests. Frontend formatting, TypeScript, Vitest and the Vite production
build run alongside the Python service and release-tool tests. Native formatting,
tests, strict Clippy and debug compilation run on macOS and Windows with Rust
1.98.1. These checks build no installer and require no detector/model downloads.

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
concurrency is separate. Main's required status remains `gates`, which runs even
after a job fails and rejects failure, cancellation, skipping or missing results.

## Packaged builds

Development runs the local service on port 8765; packaged apps start their own
service on `127.0.0.1:8766`. Only one packaged instance can use that port at a
time. Packaged models and dictionaries follow the platform's reviewed release
inputs rather than the optional development extras above. The Windows candidate
uses a CPU ONNX runtime; the macOS bundle keeps its reviewed Manga OCR runtime.

Follow the build recipes and exact-candidate checks in the
[shared release checklist](desktop-release.md),
[macOS release guide](macos-release.md), and
[Windows release guide](windows-release.md). Local macOS preparation starts
from the repository root:

```sh
bash scripts/build-macos-prerelease.sh --prepare-runtime
bash scripts/build-macos-prerelease.sh
```

The detector weight file is imported separately through **Select detector model
file**. The app verifies its checksum and copies it into its local data directory.
It does not download the file or include it in the bundle.

Packaged data is stored under macOS Application Support for the app identifier
or `%APPDATA%\com.yomimado.desktop` on Windows. This differs from the standalone
development defaults above. Packaged notices are under
`Contents/Resources/ocr/notices/` on macOS or `<install directory>\ocr\notices`
on Windows. Dictionary refresh requirements are in the
[dictionary update procedure](dictionary-updates.md).

Python packaging metadata (`*.egg-info/`) and Tauri capability schemas
(`apps/desktop/src-tauri/gen/schemas/`) are generated locally and ignored by Git.
Keep models, dictionaries, fixtures, and release evidence in their existing
local directories.
