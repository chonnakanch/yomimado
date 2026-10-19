# YomiMado (読み窓)

Read beyond the page.

YomiMado is a local-first desktop assistant for reading Japanese manga already
visible on your screen. Capture text, recognize it locally, and click an
interactive overlay to explore Japanese without replacing the original image.

## Features

- Select a screen region or scan a manga page with a reusable area fallback.
- Recognize horizontal and vertical Japanese and show aligned text regions.
- Explore word readings, dictionary meanings, kanji, and example compounds.
- Development source: show optional, offline estimated JLPT vocabulary tags in word definitions and Saved.
- Import an optional local translation model or select one through Ollama, then request translation when needed.
- Save and review words and sentences locally.

Screenshots stay local. Translation and saving require an explicit action.

## Release status

The first desktop pre-release, v0.1.0, passed macOS Apple Silicon and Windows
11 x64 acceptance and was published on 2026-10-12. On 2026-10-13 the owner removed
its tag; the public release/downloads are currently unavailable. The
[shared release checklist](docs/desktop-release.md) preserves the original exact
installer hashes, passing results, disclosed limitations and future release gates.

| Target                           | First release format                                        |
| -------------------------------- | ----------------------------------------------------------- |
| macOS 14 or later, Apple Silicon | Unnotarized hobby DMG; requires per-app Gatekeeper approval |
| Windows 11 x64                   | Unsigned per-user NSIS installer; requires WebView2         |

Detector weights are installed separately through **Select detector model file**.
The app checks the supported file's checksum before importing it. See the
[installation guide](docs/usage.md)
for installation details.

## Read a page

In the current development source:

1. Press `Cmd+Shift+O` on macOS or `Ctrl+Shift+O` on Windows, then drag over text.
2. Click a recognized region to open its learning popup.
3. Select a word or kanji, request translation, or save an entry.

For repeated scans, use **Whole Screen** or `Cmd/Ctrl+Shift+S`. **Rescan** captures
the last successful area again; scan again after changing pages. Open **More
actions → Saved** to review saved words and sentences. See the
[reading guide](docs/usage.md) for setup, keyboard navigation and the historical
v0.1.0 controls.

## Development quick start

Start the OCR service (macOS shell):

```sh
cd services/ocr
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,tokenization]'
python ../../scripts/prepare_lindera.py --download
uvicorn app.main:app --reload --port 8765
```

Start the desktop app in a second terminal:

```sh
cd apps/desktop
npm ci
npm run tauri dev
```

This minimal setup shows a labeled demo boundary until local OCR models are
configured. See [development setup](docs/development.md) for Windows commands,
models, dictionaries, translation, capture diagnostics, and packaged builds.
macOS capture requires Screen Recording permission.

## Limitations

OCR and translation can be inaccurate, especially for stylized text and complex
layouts. Recognition confidence is unknown; approximate regions are marked for
review. Page cropping may need a saved area, and estimated reading order uses
text positions rather than panel detection. There is no continuous background
OCR or automatic translation. Platform test coverage is recorded in the release
checklists.

## Project documentation

- [Documentation index](docs/README.md)
- [Project structure, runtime flow and local API usage](docs/project-structure.md)
- [Development setup and checks](docs/development.md)
- [Reading and learning guide](docs/usage.md)
- [Implementation status and remaining work](docs/implementation-plan.md)
- [Feature roadmap](docs/feature-roadmap.md)
- [Changelog](CHANGELOG.md)
- [Initial product and technical design](docs/initial-design.md)
- [App resources and data flow](docs/app-resources.md)
- [macOS release guide](docs/macos-release.md)
- [Windows release guide](docs/windows-release.md)
- [Dictionary update procedure](docs/dictionary-updates.md)

## License and credits

YomiMado's own source is licensed under [GPL-3.0-only](LICENSE). Models,
dictionaries, and other third-party components retain their separate terms.
The detector uses comic-text-detector code; recognition uses Manga OCR and
dictionaries use EDRDG data. See [third-party notices](THIRD_PARTY_LICENSES/README.md)
and [model and dictionary credits](THIRD_PARTY_LICENSES/MODEL_CREDITS.md).
