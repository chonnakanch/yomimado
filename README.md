# YomiMado

YomiMado is an open-source desktop assistant for reading Japanese manga on
macOS and Windows. It recognizes text already visible on your screen and adds
interactive learning overlays while preserving the original manga image.

**Capture → recognize → click → learn**

## Features

- Scan a selected area or detect a manga page, then reuse its bounds with Rescan.
- Recognize horizontal and vertical Japanese locally.
- Look up word readings, dictionary meanings, kanji, and example compounds.
- Adjust word boundaries manually and correct OCR text.
- Show optional estimated JLPT vocabulary tags and conjugation explanations.
- Request local translation using an imported model or Ollama.
- Save and review words and sentences locally.

These features describe the current development source. Published installers may
have different features; see the [changelog](CHANGELOG.md).

Screenshots, OCR, and dictionary lookup stay local. Translation runs only when
you request it, and saving is explicit.

## Installation

For installers and release notes, see [GitHub Releases](https://github.com/chonnakanch/yomimado/releases).

| Platform | Requirements                                                                       |
| -------- | ---------------------------------------------------------------------------------- |
| macOS    | macOS 14 or later, Apple Silicon; unnotarized DMG with per-app Gatekeeper approval |
| Windows  | Windows 11 x64; unsigned per-user installer with WebView2                          |

Follow the [installation and reading guide](docs/usage.md) for setup and platform
permissions. macOS capture requires Screen Recording permission.

Detector weights are installed separately through **Select detector model file**;
the app verifies the supported file's checksum before importing it. Translation
is optional: import a compatible local model or select one through Ollama in
**Settings → Reading**.

## Read a page

1. Open your manga in its usual reader.
2. Press `Cmd+Shift+O` on macOS or `Ctrl+Shift+O` on Windows, then drag around text.
3. Click a recognized region and select a word or kanji in the learning popup.
4. Look up a selection, request translation, or save a word or sentence.

For page scanning, use **Whole Screen** or `Cmd/Ctrl+Shift+S`. After changing
pages, **Rescan** captures the last successful area again; start a new scan if the
page moved. Open **More actions → Saved** to review saved entries.

OCR can make mistakes, especially with stylized text. **Check OCR** marks text
that needs review; use **Edit OCR text** to correct it. Reading order is estimated
from text positions, and page detection may need a saved or drawn area. See the
[reading guide](docs/usage.md) for keyboard navigation and detailed controls.

## Development

Requires Python 3.10+, Node.js/npm, Rust, and the Tauri platform prerequisites.
See [development setup](docs/development.md) for dependencies and Windows commands.

Start the local service in one terminal (macOS shell):

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

This minimal setup returns a labeled demo boundary until local OCR models are
configured. Follow the [development guide](docs/development.md) to configure OCR
models, word/kanji dictionaries, optional translation, and diagnostics.

## Documentation

- [Reading and installation guide](docs/usage.md)
- [Development setup](docs/development.md)
- [Feature roadmap](docs/feature-roadmap.md) and [changelog](CHANGELOG.md)
- [Implementation status](docs/implementation-plan.md) and [release checklist](docs/desktop-release.md)
- [Full documentation index](docs/README.md)

## License and credits

YomiMado's source is licensed under [GPL-3.0-only](LICENSE). Models, dictionaries,
and other third-party components retain their own terms.

Text detection uses comic-text-detector, recognition uses Manga OCR, and word
and kanji lookup use EDRDG dictionary data. See the
[third-party notices](THIRD_PARTY_LICENSES/README.md) and
[model and dictionary credits](THIRD_PARTY_LICENSES/MODEL_CREDITS.md).
