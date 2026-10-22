# Documentation

Start with the guide for your task. Current behavior and priorities live in the
first table; dated investigations and exact-candidate records remain separate.

## Main guides

| Guide                                                       | Use it for                                                                                           |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [Installation guide](installation-guide.md)                 | System requirements, macOS/Windows installation, detector setup, first scan and optional translation |
| [Reading guide](usage.md)                                   | Toolbar, scan modes, keyboard reading, learning popups and Saved collections                         |
| [Development](development.md)                               | Local service, models, dictionaries, checks and diagnostics                                          |
| [Implementation status and roadmap](implementation-plan.md) | Current scope, maintenance priorities, proposed features and behavior limits                         |
| [Architecture and resources](architecture.md)               | Source tree, scan flow, API boundaries, coordinates, models, dictionaries and storage                |
| [Design system](design-system.md)                           | Tokens, components, tray behavior and icon provenance/regeneration                                   |
| [UI testing](ui-testing.md)                                 | Native overlay checks, Windows scaling matrix, tray acceptance and dated redesign review             |
| [Git conventions](git-conventions.md)                       | Branches, commits, PRs and preservation of reviewed history                                          |
| [Translation model setup](translation-model-selection.md)   | Compatible local Marian imports, Ollama, selection and cache behavior                                |
| [Dictionary updates](dictionary-updates.md)                 | Snapshot replacement and attribution                                                                 |
| [Script guide](../scripts/README.md)                        | Tool entrypoints, resource preparation, builds and verification                                      |
| [Changelog](../CHANGELOG.md)                                | Dated development changes and verification limits                                                    |

For [small-text and vertical OCR accuracy](implementation-plan.md#small-text-and-vertical-ocr-accuracy),
see the initial recovery scope, measurements and remaining work.
For horizontal drag-selection outlines, see the
[geometry verification](ui-testing.md#horizontal-ocr-geometry-recovery) and
[synthetic measurement record](ocr-geometry-results.json), plus the
[mixed-content follow-up](ocr-mixed-text-results.json).

## Releases and exact acceptance

The [shared checklist](desktop-release.md) is the authority for recorded release
identities, candidate hashes, publication and retained acceptance disclosures.
Dated records apply to their stated source/candidate; source checks do not accept
a different installer.

- [Release and runtime-seed runbook](release-runbook.md): version preparation,
  [PR-based release notes](release-runbook.md#generate-and-review-release-notes),
  source review, seed build/upload, pin activation and owner publication approval.
- [Shared release checklist](desktop-release.md): exact releases, workflow gates,
  complete delivery, source/notices and protected publication.
- [v0.5.0 publication recovery](release-recovery-0.5.0.md): original verified
  installers, pinned artifacts, successful recovery and temporary workflow retirement.
- [macOS release guide](macos-release.md) and [Windows release guide](windows-release.md):
  platform packaging and dated preparation evidence.
- [macOS installed-app record](macos-clean-mac-test.md) and
  [Windows installed-app record](windows-installed-test.md): exact hashes,
  owner reports, waivers and untested hardware.
- [Verified macOS runtime seed](macos-runtime-seed.md),
  [0.2.0 source review](macos-runtime-review-0.2.0.md) and
  [0.3.0 source review](macos-runtime-review-0.3.0.md) and
  [OCR source review](macos-runtime-review-ocr-20261021.md): private input/source identities.
- [0.4.0 preparation](release-preparation-0.4.0.md) and
  [runtime reuse repair](macos-runtime-reuse-0.4.0.md): retained preparation,
  technical review and failed-run context, superseded by later release records.

## Required source, licence and rebuild records

These remain separate because packaging scripts read or ship some of them and
because they document exact distributed inputs. Keep the associated JSON files,
two Windows Cargo locks and [third-party notices](../THIRD_PARTY_LICENSES/README.md).
Do not move or remove them without updating consumers and verifying source delivery.

| Platform                                   | Records                                                                                                                                                                                                          |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| macOS                                      | [Corresponding-source review](macos-source-review.md), [minimal OpenCV](macos-opencv.md), [NumPy](macos-numpy.md)                                                                                                |
| Windows source and replacement             | [Source review](windows-source-review.md), [native replacement](windows-native-replacement.md), [NumPy runtime](windows-numpy-runtime.md), [historical Sudachi binding](windows-sudachi-runtime.md)              |
| Windows installer and Microsoft components | [NSIS runtime](windows-nsis-runtime.md), [Microsoft runtime](windows-microsoft-runtime.md), [GPL compatibility review](windows-gpl-compatibility.md), [WebView2 loader investigation](windows-webview-loader.md) |

`windows-*.json` manifests bind native sources, build inputs, runtime terms and
notices; the Cargo locks pin source builds. Benchmark JSON and the dated advisory
snapshot bind their reports below. These are maintained evidence/input files,
not disposable documentation attachments.

## Investigations and dated reviews

Keep reports that explain a current resource decision or retain reproducible
measurements. Their recommendations and test counts apply to their stated dates
and inputs; the implementation plan records the current choice.

| Subject                 | Retained reports                                                                                                                                                                                                                                                                                     |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tokenizer choice        | [Lindera migration](lindera-migration.md), [original Lindera experiment](lindera-tokenizer-experiment.md), [candidate comparison](tokenizer-candidate-comparison.md), [SudachiPy investigation](sudachipy-investigation.md), [tokenizer resource investigation](tokenizer-resource-investigation.md) |
| OCR size and accuracy   | [Optional translation and OCR reduction](optional-translation-and-ocr-size.md), [private packaging/real-page acceptance](resource-reduction-acceptance.md), [scan performance comparison](scan-performance-comparison.md), [detector retry optimization](detector-retry-optimization.md)             |
| macOS inference options | [ONNX investigation](macos-onnx-investigation.md), [decoder cache/CoreML follow-up](macos-onnx-cache-coreml.md)                                                                                                                                                                                      |
| Code and security       | [Code review, 2026-10-13](code-review-2026-10-13.md), [security review, 2026-10-13](security-review-2026-10-13.md), [advisory snapshot](security-advisory-snapshot-2026-10-13.json)                                                                                                                  |
