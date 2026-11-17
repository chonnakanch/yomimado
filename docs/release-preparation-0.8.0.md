# v0.8.0 release preparation

Prepared **2026-11-17** on `release/0.8.0` from main
`42005f9d927f735624aaa313e383cdb4c7d8d651`. The five app version files agree on
**0.8.0**. The version and replacement runtime source is
`6af1644cfccda05c867460438b4d44845cbec8e7`; preserve that commit when merging.

GitHub's generated notes since published
[v0.7.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.7.0)
list [Windows OCR scheduling (#48)](https://github.com/chonnakanch/yomimado/pull/48)
and the [Auto detect page-turn fix (#47)](https://github.com/chonnakanch/yomimado/pull/47),
followed by the
[Full Changelog comparison](https://github.com/chonnakanch/yomimado/compare/v0.7.0...v0.8.0).
Windows starts reading initial text regions while the detector works on tile and
mask retries. Auto detect sees changes below translucent OCR highlights, so it
can rescan when the mouse stays still and the page changes. Native Windows
latency and the original reader interaction remain unverified.

Release uses the `macos-15` Arm64 runner, matching Checks, because
[GitHub retired the macOS 14 runner](https://github.com/actions/runner-images/issues/13518).
The host image change does not alter the app's configured macOS deployment target,
reviewed runtime dependency pins, Windows inputs or publication gates.
The [base Checks run](https://github.com/chonnakanch/yomimado/actions/runs/43829991624)
passed on both platforms, including macOS 15.

## Verification

- Frontend: formatting, TypeScript, **477 tests** and production build with Node 22.23.2.
- Service and OCR contracts: Ruff lint/format and **311 tests**, no skips, with Python 3.11.17.
- Local macOS native: formatting, strict Clippy, **104 tests** and debug build with Rust 1.98.1.
- Release tools: **166 tests**, version plan, script lint/format and pinned actionlint 1.7.7.

Local logs and GitHub-generated notes are retained under
`services/ocr/build/release-0.8.0/`. Exact PR Checks and installer acceptance are
separate from these source checks.

## macOS seed

Seed `2059ccb` is incompatible: #48 changes shared packaged Python OCR source
even though concurrent detection and recognition is enabled on Windows only.
No dependency, model, dictionary pin or reuse guard was changed. The new private
candidate and unsigned source/licence review are under
`services/ocr/build/runtime-seed-6af1644/`. The previous owner's source approval
does not extend to this revision.

After exact source approval, rebuild and verify the reviewed seed, stage the four
private inputs, and activate by uploading the owner manifest last. Merge only when
authorized, with current PR Checks passing and the reviewed source history
preserved. Release runs after successful Checks on the exact main merge. Both
resulting installers still require hash-bound acceptance and separate owner
publication approval.
