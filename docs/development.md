# Development

Run commands below from the repository root unless a `cd` is shown. The desktop
requires Node.js, npm, Rust, and Tauri platform prerequisites. The development
OCR service requires Python 3.9 or later; release builders use their pinned
interpreters and dependencies.

## Start the app

Start the OCR service in one terminal (Python 3.9+):

```sh
cd services/ocr
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,tokenization]'
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
VITE_CAPTURE_DEBUG=1 npm run tauri dev
```

After selecting a region or scanning a page, the debug view shows the captured
image, final OCR polygons, detector candidate boxes, and their individual crops
and recognitions. Medium and large captures receive a bounded retry on
overlapping image tiles; duplicate boxes are merged, and the detector list
labels tile results.
Gray boxes were filtered; their reasons appear in the detector list. The first
filter only removes nearly uniform crops and recognized text
without Japanese characters. It does not reliably distinguish manga artwork
from text when OCR hallucinates Japanese. Captures are held in memory, not saved
as PNG files. On the first launch after this change, YomiMado removes its older
`capture-<number>.png` files from its own captures cache. For a small selection
with one incomplete or missing detector region, the service also tries Manga OCR
on the whole selected crop. If it recovers plausible text, the overlay uses a
dashed, approximate selection-area box rather than claiming precise text
geometry. Choose **Show overlay** to continue or **Close** to cancel. This flag is read when Vite
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

The on-demand popup can translate Japanese text to English with the free,
user-installed [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en)
model. This is a baseline model, not a manga-specific or contextual translator.
Neither model weights nor Japanese text are sent to a cloud translation service
at runtime. No model is downloaded by YomiMado itself.

Install the optional Python dependencies in the OCR service environment and
download the model to the git-ignored local model directory:

```sh
cd services/ocr
pip install -e '.[dev,translation]'
hf download Helsinki-NLP/opus-mt-ja-en --local-dir ./local-models/opus-mt-ja-en
export YOMIMADO_TRANSLATION_MODEL="$PWD/local-models/opus-mt-ja-en"
uvicorn app.main:app --reload --port 8765
```

The popup reports a setup error until the model and optional dependencies are
available. Successful translations are cached locally in
`~/.cache/yomimado/translation.sqlite3` (override with
`YOMIMADO_TRANSLATION_CACHE`). Only the selected Japanese text is sent from
the desktop window to this loopback service; screenshots are not submitted for
translation. The service configures a CORS origin allowlist for the Tauri app and
the development frontend. This is not request authentication.

## Japanese tokenization

The `tokenization` Python extra installs pinned SudachiPy 0.6.10 and the
Sudachi core dictionary 20250515. It works without a translation model or
network service. The selected OCR string is sent to the local
`POST /api/v1/tokenize` endpoint when its popup opens; edited text is analyzed
again only when **Analyze words** is pressed. The endpoint preserves the exact
input and returns Unicode code-point offsets for word tokens. It omits
punctuation-only and symbol-only study tokens, while keeping punctuation in the
source sentence for translation. Readings are displayed in Sudachi's katakana
form. The popup offers precise word selection in the OCR text, not directly on
the manga image; the detector currently provides region polygons, not
per-character positions. If the extra is not installed, OCR and translation
continue to work and the popup shows a tokenization setup error.

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
local OCR service. Inflected words also try their Sudachi dictionary form.
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
