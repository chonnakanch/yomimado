# Retired workflow records

These six workflow definitions are archived byte-for-byte from `bd137ef` after
the first desktop pre-release completed. GitHub Actions discovers workflows in
`.github/workflows/`; these copies are historical documentation. Their original
triggers, input hashes and permissions describe their past execution, not a
supported dispatch path. Do not copy them back to run a new release.

| Archived definition                                      | Why retired                                                                                                                                        |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| [desktop-release-resume.yml](desktop-release-resume.yml) | One-candidate v0.1.0 recovery completed; its original artifact, source and installer hashes cannot be reused for future releases.                  |
| [windows-geos-audit.yml](windows-geos-audit.yml)         | Replacement experiment against private setup `51b0091103c1…`; current delivered sources and replacement instructions preserve its review evidence. |
| [windows-onnx-prototype.yml](windows-onnx-prototype.yml) | ONNX feasibility is established; preparation, export, parity and installed runtime verification are integrated into installer builds.              |
| [windows-opencv-audit.yml](windows-opencv-audit.yml)     | The IPP-free OpenCV build and frozen detector checks run through the Windows installer recipe.                                                     |
| [windows-vc-provenance.yml](windows-vc-provenance.yml)   | The canonical runtime reference is recorded; current builds check/stage the reviewed VC inputs.                                                    |
| [webview-loader-probe.yml](webview-loader-probe.yml)     | Source loader preparation and verification run through Windows packaging.                                                                          |

The original audit, rebuild and provenance scripts remain available. Some are
called by normal packaging, others document component replacement/reproduction.
Licence notices, source manifests, test fixtures and public release assets are
preserved. Historical Actions runs/artifacts are not deleted by this cleanup;
GitHub may continue displaying a retired workflow's run history.

The three routine workflows are:

- [Desktop release from main](../../.github/workflows/macos-prerelease.yml):
  automatic macOS/Windows builds and one protected publisher.
- [Desktop release gate checks](../../.github/workflows/desktop-release-checks.yml):
  lightweight required checks on develop/main and main pull requests.
- [Windows private candidate](../../.github/workflows/windows-candidate.yml):
  development-only installed verification and private candidate staging.

This retirement is prepared on `develop`. An authorized merge through protected
`main` is required to retire the default branch's definitions too. Existing main
protection and owner publication review stay in place.
