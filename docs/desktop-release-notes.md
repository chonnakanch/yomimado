# YomiMado VERSION — CLASSIFICATION

YomiMado (読み窓) helps Japanese learners read manga already visible on their
screen: capture a region, recognize Japanese locally, then click to view readings,
dictionary/kanji information and an on-demand local translation. Saved words,
sentences and translation cache stay on the computer.

## Changes in VERSION

- Select Japanese text within or across automatic word boundaries and look up
  the selection in local JMdict. A visible caret and keyboard selection help
  refine the span; matches can be saved with their original sentence context.
- Expand Conjugation in word details for common verb and i-adjective forms,
  including ちゃう／じゃう contractions. Unsupported forms remain explicit;
  explanations do not infer context-dependent meanings.
- Estimated JLPT N5–N1 vocabulary badges use 8,113 locally bundled
  spelling/reading pairs. Unlisted words stay unclassified, and Reading settings
  can hide the badges. Jonathan Waller / Stephen Kraus attribution and the
  dataset's separate CC BY-SA 4.0 licence appear in Sources & licenses.
- Search Saved words by spelling, dictionary form, reading, meaning or source,
  and sentences by Japanese or saved translation. Search ignores kana, width
  and case differences, and remembers a separate query for each collection.
  The library uses larger headwords, numbered meanings and expandable details.
- The toolbar's More actions menu measures its complete content before opening,
  keeping Quit reachable and avoiding repeated resizing on constrained screens.

Check OCR remains an uncertainty indicator. Manual OCR correction and ordinary
Rescan remain available; single-bubble retry/redraw is deferred.

## Downloads and installation

Download the Apple Silicon `.dmg` for macOS or the per-user Windows 11 x64
`_x64-setup.exe`. Windows inference uses the CPU and requires no developer Python
or CUDA. Paid code signing is not used for this hobby release; macOS is ad-hoc
signed and unnotarized. Follow the operating system's per-app approval flow and
keep security protections enabled. Unexpected malware/damaged-file warnings need
investigation.

Import your own compatible detector ONNX file through model setup. Detector
weights are excluded from the installer, release assets and corresponding sources.
Windows setup requires acceptance of terms applying only to Microsoft's runtime
components; YomiMado's GPL and other open-source component rights remain intact.

Corresponding project/dependency sources, build recipes, licences, data notices
and checksums accompany both installers. Source-only rebuilding of the complete
delivery remains unverified. Hardware coverage and fresh-machine limitations are
disclosed below; a successful hosted build is separate from installed-app testing.

Local Marian import formats differ by platform: macOS accepts compatible single
Torch/Safetensors weights with tokenizer files; Windows requires the compatible
Marian ONNX export folder. GGUF and other model families use Ollama. See
[translation model setup](https://github.com/chonnakanch/yomimado/blob/main/docs/translation-model-selection.md).
Ollama must be installed separately on the same computer.

Only the installer for your platform is needed to run YomiMado. Translation models
are separate optional downloads. For the complete corresponding-source delivery,
download both `YomiMado_VERSION_sources_macos.tar.gz` and
`YomiMado_VERSION_sources_windows.tar.gz`. Together they retain the original
platform source archives, project sources, build recipes and exact dictionary
snapshots. Extract the outer archives, then the archives inside them; each retains
its original paths. `YomiMado_VERSION_notices.tar.gz` contains the platform
notices, native input inventory and original verification records. The single
`desktop-SHA256SUMS.txt` checks both installers, both source archives, notices,
optional translation ZIPs and `desktop-release-candidate.json`, which records
provenance and original input hashes. GitHub's automatic repository source
downloads do not contain all bundled dependency sources.
