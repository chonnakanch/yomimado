# Third-party licensing and pre-release audit

YomiMado's own source is GPL-3.0-only. This file tracks the separately licensed
software and assets needed for the first **self-contained macOS package**. It
is an audit, not yet the complete set of license texts for a distributable
build. Do not describe the package as release-ready until the open items below
are closed and the final bundle has been inspected.

| Component | Intended package use | License evidence | Status |
| --- | --- | --- | --- |
| [comic-text-detector source](https://github.com/dmMaze/comic-text-detector) | Text detection code | Repository declares GPL-3.0 | Source terms identified; retain notices and corresponding source. |
| [`comictextdetector.pt.onnx`](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1) | Text detection weights | The detector project points to this release, but the release does not explicitly license the weight file | **Redistribution terms unresolved. Do not publicly ship this asset yet.** |
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
final distributable package must include a generated, verified inventory and
the required license/notice texts for the **actual** compiled and frozen
dependencies, not only this direct-dependency summary.

## Open release gates

1. Obtain clear redistribution terms from the detector-weight publisher or
   choose an equivalently functional detector asset with explicit distributable
   terms. A local-only test build can use the user's existing copy, but it
   must not be shared as a public pre-release while this remains unresolved.
2. Pin model and dictionary revisions/checksums and identify any required
   model-card or dataset notices for the exact files selected.
3. Generate and review the complete macOS bundle's dependency/asset notice
   set, including full licence texts and corresponding-source obligations.
4. Verify those notices and the EDRDG source/attribution are accessible from
   the packaged app or its accompanying distribution materials.
