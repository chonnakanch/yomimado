# git-cliff — maintainer release-note tool

Exact version: **2.14.2**, upstream tag
[`v2.14.2`](https://github.com/orhun/git-cliff/tree/v2.14.2).
Its [package manifest](https://github.com/orhun/git-cliff/blob/v2.14.2/git-cliff/Cargo.toml)
declares `MIT OR Apache-2.0`; YomiMado uses the MIT option and retains the exact
upstream [LICENSE-MIT](LICENSE-MIT).

This standalone tool generates draft Markdown from local Git history. It is not
an app dependency, is not frozen into OCR, and is not bundled with installers.
Downloaded binaries stay in ignored `services/ocr/build/release-tools/`, separate
from the reviewed Python runtime. There are no model/data assets involved.

`scripts/release_notes.py` pins these upstream release assets to the SHA-256
digests reported by GitHub's exact-version release API on 2026-10-20:

| Target                   | Archive SHA-256                                                    |
| ------------------------ | ------------------------------------------------------------------ |
| macOS Apple Silicon      | `a0be97e237d440d34c5e508ec21d070b2c85cbb8be48a46a56f9a4e8bd247f05` |
| Windows x64              | `6ece2112b3f4af462190ecbea4aeb1315fff6af415629b597f84319073c31131` |
| Linux x64 (CI host only) | `24f397c733add5390fdceee3a2088588ab0d5f944ce00d34cb7029b888cf2db4` |

Preparation downloads only the selected platform's archive from the original
[release](https://github.com/orhun/git-cliff/releases/tag/v2.14.2), verifies it and
extracts only its regular executable member. Generation rechecks the archive hash
and executable bytes, and invokes the tool with `--offline --no-exec`. No GitHub
credential is needed to prepare the public tool or generate local drafts.

The config and wrapper are independent maintainer tooling, permitted by exact
paths in the macOS reuse guard. They do not extend source approval to new frozen
runtime/dependency inputs or alter publication protections. See the
[runbook](../../docs/release-runbook.md) for note review and release steps.
