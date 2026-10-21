# v0.5.0 release preparation — 2026-10-21

Version: **0.5.0**, classified as a pre-release by the existing version policy.
Preparation branch: `release/0.5.0`, based on main after
[PR #26](https://github.com/chonnakanch/yomimado/pull/26) merged at `15bcd27`.
The five npm/Tauri/Cargo app version files change together; dependency versions,
locks apart from the app version, runtime pins and release workflow stay intact.

## Source and release notes

The comparison starts at published `v0.4.0` (`bfdcbf2`). Its merged PRs cover
release/branch maintenance, installation/documentation, initial small-selection
OCR recovery in [PR #24](https://github.com/chonnakanch/yomimado/pull/24), and
custom capture shortcuts in PR #26. The shortcuts retain their own merged PR entry.
No removed bubble retry/redraw feature is being restored or advertised.

Public notes use GitHub's PR titles/numbers and end with
[Full Changelog](https://github.com/chonnakanch/yomimado/compare/v0.4.0...v0.5.0).
The publisher generates its source/hash-bound preview from the resulting main
merge, following the [release-note procedure](release-runbook.md#generate-and-review-release-notes).
Installation stays in the installation guide; verification evidence stays here
and in downloadable metadata. No public tag is created during preparation.

## Reviewed seed compatibility

The active macOS seed is `46a5649007caf09538adb7d7d0bc4bda763c095e`, private label
`macos-reviewed-seed-46a5649`. It already includes the OCR recovery. Its source
approval, four exact input hashes and retained limits are recorded in the
[OCR seed review](macos-runtime-review-ocr-20261021.md).

All four retained local inputs pass exact membership/hash verification with
`scripts/desktop_release.py verify-inputs --platform macos`. Their original
0.4.0 filenames identify the seed; CI rebuilds React/Rust for 0.5.0 and copies the
reviewed frozen runtime. The optional Torch archive is copied under the current
release filename while preserving its bytes. Windows input pins are unchanged.

The committed-source `verify-reuse` guard remains required before integration.
No guard exception, source approval or runtime/dependency change is introduced
by this version preparation.

## Local verification

Using the existing test-only Python 3.11 environment, without installing test
tools into the reviewed frozen runtime:

- Frontend: formatting, TypeScript, all **301 tests**, production build.
- Service/contracts: Ruff lint/format and **212 tests**, with no skips reported.
- macOS native: Rust formatting, strict Clippy, all **75 tests**, debug build.
- Release tools: **151 tests** across macOS release/source/notices, shared release
  and publisher, runtime rules, version updater, PR notes and JLPT provenance.
- All release scripts pass Ruff lint/format; both workflows pass pinned actionlint.
- Version plan reports `0.5.0`, tag `v0.5.0`, `prerelease=true`.

The frontend build retains its existing large-chunk advisory. These are source
and debug checks; no new macOS or Windows installer is built or accepted locally.
Hosted Checks must pass for the final release PR and again for the resulting
exact main commit before the automatic Release builders proceed.

## Remaining gates and limits

Merging the release PR starts Release automatically after exact-main Checks.
Download the combined verified candidate, record its actual hashes and test the
exact installers before the owner's protected `desktop-release` publication
approval. Keep main at the candidate source through publication.

The prior manual shortcut pass applies to source `f65576c`; it is not acceptance
of a new 0.5.0 installer. Native Windows interaction, real manga OCR evaluation,
full filtered-source-only rebuilding and existing hardware/waiver limits retain
their recorded scope. macOS remains ad-hoc signed and unnotarized. This preparation
adds no installer acceptance or publication approval.
