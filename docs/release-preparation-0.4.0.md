# Version 0.4.0 preparation — 2026-10-20

Follow-up: the owner merged PR #17 at `ce2a3df`; Release `39371691358` then failed
in `plan` at the recorded reuse rejection, before either builder ran. The
[subsequent technical review and repair](macos-runtime-reuse-0.4.0.md) covers the
exact frontend data separately and adds the real preflight to required Checks.
The preparation evidence and original blocker below are retained historically.

Scope: prepare from `develop`, run the release checks and stop before merging or
publishing. Preparation started from clean, fetched `develop` at
`1111f874aa91ea157e33bb4ec8f6ac5ad8c51a0f`, matching `origin/develop`.
The five npm/Tauri/Cargo version files now agree on `0.4.0` (pre-release), using
`scripts/update_version.py` after its dry run. The
[release notes at the preparation commit](https://github.com/chonnakanch/yomimado/blob/eb77c5341db66657c270e9fd6b10916f874e2ae8/docs/desktop-release-notes.md) preserve `VERSION` and `CLASSIFICATION`
and describe the final feature set, including the deferred bubble retry and the
current separate platform source archives.

## Seed compatibility: blocked

The enforced `scripts/macos-ci-release.py verify-reuse` check rejects this source.
Its first rejection is `CHANGELOG.md`; a diagnostic that checks each changed path
independently identifies all 14 rejected paths:

- `CHANGELOG.md`
- `THIRD_PARTY_LICENSES/ASSET_NOTICES.md`
- `THIRD_PARTY_LICENSES/README.md`
- `THIRD_PARTY_LICENSES/jlpt/LICENSE.txt`
- `THIRD_PARTY_LICENSES/jlpt/README.md`
- `THIRD_PARTY_LICENSES/jlpt/UPSTREAM_README.md`
- `THIRD_PARTY_LICENSES/jlpt/source/index.json`
- `THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_1.json`
- `THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_2.json`
- `THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_3.json`
- `THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_4.json`
- `THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_5.json`
- `THIRD_PARTY_LICENSES/jlpt/sources.json`
- `scripts/prepare_jlpt.py`

The frozen service under `services/ocr/`, macOS freeze/source-collection recipes
and dependency versions are unchanged from reviewed seed
`f1b4fbaa8980ff0df0a1abf6f5a93df058f4678e`. The new JLPT data is embedded in the
rebuilt frontend and carries separate CC BY-SA 4.0 terms; its retained inputs,
generator and complete licence pass provenance checks. This is evidence for a
source/data review, not a passing reuse decision or new owner approval. In
particular, the existing CI follow-up's assertion that licence choices are
unchanged cannot simply be extended to this new dataset without review.

The current seed revision, macOS input hashes, workflow paths and Windows pins
remain unchanged. `desktop_release.py verify-inputs --platform macos` passes for
all four retained files in ignored
`services/ocr/build/release-0.3.0/seed-reviewed/`; their exact hashes and historical
uploaded verification remain in the [seed record](macos-runtime-seed.md).
No new input upload or independent live draft verification is claimed here.
The existing owner's source approval covers that recorded seed only.

Before main integration, resolve the source/data/notice review boundary with a
separately reviewed, narrowly scoped runtime-independent reuse change, or prepare
and approve a replacement seed under the [runbook](release-runbook.md). Neither
the allowlist nor the revision pin was changed to make this check pass. A draft
PR must remain blocked until the committed-source guard passes.

## Verification

All checks below pass locally on macOS Apple Silicon unless marked blocked:

| Check                                                 | Result                                                 |
| ----------------------------------------------------- | ------------------------------------------------------ |
| Version updater dry run and five-file consistency     | `0.4.0`, pre-release; only version fields changed      |
| Frontend tests                                        | 288 passed in 26 files                                 |
| Frontend Prettier, TypeScript and production build    | Passed                                                 |
| Model-free service/OCR contract selection from Checks | 187 passed, zero skips                                 |
| Service Ruff check and format                         | Passed                                                 |
| Selected release-tool suites                          | 128 passed                                             |
| Script Ruff check and format                          | Passed                                                 |
| Pinned actionlint 1.7.7, both workflows               | Passed                                                 |
| JLPT retained-source reproduction                     | All 8,113 spelling/reading labels and licence verified |
| Rust 1.98.1 formatting and strict all-target Clippy   | Passed                                                 |
| Rust tests and native debug build                     | 70 tests passed; build passed                          |
| Existing local macOS seed inputs                      | All four files match active hash pins                  |
| Committed-source runtime reuse                        | **Blocked**, rejected paths above                      |

The selected release-tool suites are `test_macos_release.py`,
`test_macos_sources.py`, `test_macos_notices.py`, `test_desktop_release.py`,
`test_release_rules.py`, `test_update_version.py` and `test_prepare_jlpt.py`.
Python checks use the existing Python 3.11.17 verification environment, separate
from the reviewed runtime. The host's default `python3` lacks `tomllib` and is
unsuitable for these scripts. Frontend build retains Vite's non-fatal 500 kB
chunk-size warning; no threshold was relaxed.

No installer was built or accepted for 0.4.0. Windows native verification runs
through the PR's required Checks; local Windows interaction, mixed-DPI hardware
and both exact-installer checklists remain separate. No main integration, Release
dispatch, public tag, seed approval, installer acceptance or publication occurred.
The historical 0.3.0 run and its approval boundaries remain unchanged.
