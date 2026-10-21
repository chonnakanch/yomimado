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

See [release notes](https://github.com/chonnakanch/yomimado/releases) for each
installer's features and [CHANGELOG.md](CHANGELOG.md) for development changes.

Screenshots, OCR, and dictionary lookup stay local. Translation runs only when
you request it, and saving is explicit.

## Installation

Download the macOS Apple Silicon or Windows 11 x64 installer from
[GitHub Releases](https://github.com/chonnakanch/yomimado/releases).
Follow the [installation guide](docs/installation-guide.md) for system requirements,
installation, detector setup, permissions, your first scan and optional translation.

## Read a page

Select a visible Japanese text area, click a recognized region and explore words,
kanji or an explicitly requested translation. Use Rescan after turning a page and
save entries when you want to keep them. See the [reading guide](docs/usage.md)
for controls, keyboard navigation and OCR correction.

## Development

Follow [development setup](docs/development.md) for prerequisites, source-checkout
commands, models and checks. Use the [Git conventions](docs/git-conventions.md)
for branches and PRs; release preparation follows the
[release runbook](docs/release-runbook.md).

## Documentation

- [Installation guide](docs/installation-guide.md), [reading guide](docs/usage.md) and [translation model setup](docs/translation-model-selection.md)
- [Development setup](docs/development.md) and [architecture/resources](docs/architecture.md)
- [Implementation status and feature roadmap](docs/implementation-plan.md)
- [Design system](docs/design-system.md) and [native UI testing](docs/ui-testing.md)
- [Release runbook](docs/release-runbook.md) and [exact release/installer records](docs/desktop-release.md)
- [Changelog](CHANGELOG.md) and [full documentation index](docs/README.md)

Installation and usage guides cover the packaged app. Development and architecture
guides cover the source checkout. Dated reviews and release records retain their
exact source/installer scope and acceptance limits.

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
