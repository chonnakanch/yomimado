# Retired workflow records

The six audit/recovery definitions are archived byte-for-byte from `bd137ef`;
the private Windows candidate definition is preserved from `9e12956`. All were
retired after the first desktop pre-release completed. GitHub Actions discovers workflows in
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
| [windows-candidate.yml](windows-candidate.yml)           | The maintainer chose main-only release builds; the shared Release workflow builds and verifies Windows directly.                                   |

The original audit, rebuild and provenance scripts remain available. Some are
called by normal packaging, others document component replacement/reproduction.
Licence notices, source manifests, test fixtures and public release assets are
preserved. Historical Actions runs/artifacts are not deleted by this cleanup;
GitHub may continue displaying a retired workflow's run history.

The two routine workflows are:

- [Release](../../.github/workflows/release.yml):
  automatic macOS/Windows builds and one protected publisher.
- [Checks](../../.github/workflows/checks.yml):
  lightweight required checks on develop/main and main pull requests.

The previous filenames `macos-prerelease.yml` and `desktop-release-checks.yml`
are now `release.yml` and `checks.yml`. Only their filenames/display names change;
the required `gates` job, main-only release trigger, two builders and protected
publisher remain unchanged. Original v0.1.0 run identities retain their old
workflow path in historical recovery verification.

This retirement is prepared on `develop`. An authorized merge through protected
`main` is required to retire the default branch's definitions too. Existing main
protection and owner publication review stay in place.
