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
- Save, search, and review words and sentences locally.

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

Follow [Install and set up](docs/usage.md#install-and-set-up) for the download,
macOS/Windows installer steps and required detector import, then
[make your first scan](docs/usage.md#make-your-first-scan). Packaged apps start their
local service automatically; no developer tools are needed. macOS capture requires
Screen Recording permission.

Download the Apple Silicon `.dmg` for macOS or the per-user Windows 11 x64
`_x64-setup.exe`. Only your platform's installer is needed to run YomiMado.
Windows inference uses the CPU and requires no developer Python or CUDA.
Translation components and models are separate optional downloads.

Paid code signing is not used for this hobby release; macOS is ad-hoc signed and
unnotarized. Follow the operating system's per-app approval flow and keep security
protections enabled. Unexpected malware/damaged-file warnings need investigation.
Windows setup requires acceptance of terms applying only to Microsoft's runtime
components; YomiMado's GPL and other open-source component rights remain intact.

Detector weights are excluded from installers, release assets and corresponding
sources. Import your compatible detector ONNX file through **Select detector model
file**; the app verifies its checksum. Translation is optional and configured in
**Settings → Reading**.
For local Marian translation, macOS accepts compatible single Torch/Safetensors
weights with tokenizer files; Windows requires the compatible Marian ONNX export
folder. GGUF and other model families use Ollama, installed separately on the same
computer. See [translation model setup](docs/translation-model-selection.md).

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

Use a short-lived branch from `main` and open a PR into `main`. Merges run CI.
To release, prepare a version on `release/<version>` and merge its PR into `main`;
Release starts automatically, waits for main Checks and builds both installers.
Publication requires separate owner approval.
See [branch and commit rules](docs/git-conventions.md).

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

- [Installation and first scan](docs/usage.md#install-and-set-up) and [translation model setup](docs/translation-model-selection.md)
- [Development setup](docs/development.md) and [architecture/resources](docs/architecture.md)
- [Implementation status and feature roadmap](docs/implementation-plan.md)
- [Design system](docs/design-system.md) and [native UI testing](docs/ui-testing.md)
- [Release runbook](docs/release-runbook.md) and [exact release/installer records](docs/desktop-release.md)
- [Changelog](CHANGELOG.md) and [full documentation index](docs/README.md)

The guides describe current development source. Dated reviews and release records
retain their exact source/installer scope; use the release records for published
versions and acceptance limits.

## License and credits

YomiMado's source is licensed under [GPL-3.0-only](LICENSE). Models, dictionaries,
and other third-party components retain their own terms.

Text detection uses comic-text-detector, recognition uses Manga OCR, and word
and kanji lookup use EDRDG dictionary data. See the
[third-party notices](THIRD_PARTY_LICENSES/README.md) and
[model and dictionary credits](THIRD_PARTY_LICENSES/MODEL_CREDITS.md).

### Sources and licenses

Each release includes corresponding project/dependency sources, build recipes,
licences, data notices and checksums. For the complete source delivery, download
both `YomiMado_<version>_sources_macos.tar.gz` and
`YomiMado_<version>_sources_windows.tar.gz`. Extract each outer archive and then
the archives inside; original paths, platform source archives and dictionary
snapshots are retained. GitHub's automatic source-code downloads do not include
all bundled dependency sources.

`YomiMado_<version>_notices.tar.gz` contains platform notices, the native input
inventory and original verification records. `desktop-SHA256SUMS.txt` checks the
installers, sources, notices, optional translation ZIPs and
`desktop-release-candidate.json`, which records provenance and original input
hashes. Complete source-only rebuilding remains unverified. Installed-app testing
and hardware limits apply to the exact installer hashes recorded for each release.
