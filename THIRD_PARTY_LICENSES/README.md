# Third-party licensing and pre-release audit

YomiMado's own source is GPL-3.0-only. This file tracks the separately licensed
software and assets needed for the first macOS package. The build now creates
`THIRD_PARTY_SOFTWARE.md`, a machine-readable manifest, and copied license
texts from its actual dependency inputs. A strict check fails the build if a
listed software component lacks a license identifier or notice file. This is
an inventory, not a legal opinion; inspect the final bundle before publishing.
The private Apple Silicon test bundle includes the assets below except the
detector ONNX weights, and retains [explicit model/dictionary credits](MODEL_CREDITS.md)
and [asset notices](ASSET_NOTICES.md). It must not be uploaded or redistributed
while signing and final release verification remain open.

| Component | Intended package use | License evidence | Status |
| --- | --- | --- | --- |
| [comic-text-detector source](https://github.com/dmMaze/comic-text-detector) | Text detection code | Repository declares GPL-3.0 | Source terms identified; retain notices and corresponding source. |
| [`comictextdetector.pt.onnx`](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1) | User-installed text detection weights; omitted from the app bundle | The detector project points to this release, but the release does not explicitly license the weight file | Do not redistribute; app verifies the selected file's checksum. |
| [Manga OCR 0.1.16](https://pypi.org/project/manga-ocr/0.1.16/) and [`kha-white/manga-ocr-base`](https://huggingface.co/kha-white/manga-ocr-base) | Japanese recognition | Software and model card state Apache-2.0 | Model terms identified; pin model revision, retain Apache notice/license. |
| [SudachiPy 0.6.10](https://pypi.org/project/SudachiPy/0.6.10/) and [SudachiDict-core 20250515](https://pypi.org/project/sudachidict-core/20250515/) | Tokenization | Package releases state Apache-2.0 | Terms identified; inventory packaged data and notices. |
| [JMdict](https://www.edrdg.org/edrdg/licence.html) and [KANJIDIC2](https://www.edrdg.org/edrdg/licence.html) | Local word/kanji data | EDRDG dictionary licence: CC BY-SA 4.0 | Redistribution is allowed with attribution and ShareAlike obligations; bundle the official files and their documentation/licence, and retain on-screen attribution. |
| [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en) | On-demand local translation | Model card states Apache-2.0 | Model terms identified; pin revision and include notice/license. |

The JMdict and KANJIDIC2 files are copyright James William Breen and the
Electronic Dictionary Research and Development Group. YomiMado uses them for
word and kanji information. The official licence and source are at
<https://www.edrdg.org/edrdg/licence.html>. Word and kanji popups already
attribute EDRDG; the packaged documentation and licence must also remain
available to users. If these files are modified, document the changes and
comply with the dictionary's ShareAlike terms.

Other direct runtime software includes Tauri, the global-shortcut plugin,
xcap, core-graphics, React, FastAPI, Uvicorn, Transformers, PyTorch,
SentencePiece, and their resolved dependencies. The Python environment,
Cargo.lock, and package-lock.json determine the exact bundled versions. A
final distributable package includes a generated, verified inventory and
license/notice texts for the **actual** compiled and frozen dependencies, not
only this direct-dependency summary. Missing wheel/crate notice files are
vendored from commit-pinned upstream repositories under `upstream/`; their
source URLs and SHA-256 digests are in `upstream/sources.json`.

## Open release gates

1. Recheck every public build for detector ONNX weights and copyrighted sample
   images; neither may be included in the package. If bundling the detector
   weights later, first obtain clear redistribution terms from their creator or
   publisher, or use a replacement asset with explicit distributable terms.
2. Recheck the final package's generated software/asset manifests and tests,
   including model SHA-256 values and dictionary refresh date.
3. Complete Apple Developer ID signing, notarization, and a clean-Mac install
   test before a direct public download. Until then the `.app` is for private
   local testing only.
