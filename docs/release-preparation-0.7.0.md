# v0.7.0 release preparation

Prepared **2026-10-28** on `release/0.7.0` from main
`91f8630` (PR #45). The five app version files agree on **0.7.0**;
the exact version/runtime source is
`2059ccbbc16dcd8a102eba00ae71b8dcee92a42f`. Preserve that commit when merging.
Main integration, source approval and installer publication remain separate.

## Changes and public notes

The previous published app release is
[v0.6.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.6.0), source
`e1d75bd4e8aab9d659bf22f089070dd2a1328f3e`. GitHub reports publication on
2026-10-22 with nine uploaded assets. This observation adds no installer acceptance.

The authenticated GitHub preview for the exact v0.7.0 source lists PRs **#39–#45**:
OCR fragment/warning and IME fixes; continuing/desire and expanded conjugation
explanations; local saved-library backup/restore; automatic bubble translation;
saved-vocabulary highlights; and opt-in page-change detection. The final diff and
changelog retain these features. Bubble translation defaults off and is configured
in Settings; Auto detect defaults off and watches an explicitly scanned fixed area.

Public notes contain the generated PR list and the final
[Full Changelog](https://github.com/chonnakanch/yomimado/compare/v0.6.0...v0.7.0)
link. The local JSON/Markdown preview is retained under
`services/ocr/build/release-0.7.0/`; CI generates its final exact-main preview after
authorized integration. Installation and verification remain outside the public body.

## Runtime reuse and replacement candidate

The existing approved `194dd57` seed cannot be reused. The strict comparison rejects
the changed toolbar configuration; the Python API, backup, vocabulary, security,
Ollama translation and OCR service sources also changed. Dependency versions,
model/data pins and build recipes are unchanged. No reuse guard was widened.

A new **private, unapproved** candidate was built from `2059ccb`. Its unsigned
source/licence delivery covers 476 component/native records and 76 archives;
all 75 reused original dependency archives were hash-verified. Generated dependency
and native inventories match the previously reviewed inputs.
Independent comparison verifies 163,833 retained files across 107 containers,
with 2,347 documented asset/vendor-map changes and no filtering changes to code
or notices. Structural validation finds no missing sources or notices.

The local review package is
`services/ocr/build/runtime-seed-2059ccb/REVIEW.md`, with delivery
`source-delivery-2059ccb/`. Unsigned worksheet SHA-256:
`4a56ed7ee44d790d7239fdbf5fad69478ba4b1ccb7715ddf3261aaf1c2023fd2`.
The worksheet has no reviewer/date and no approved `source-delivery.json` exists.
No new seed has been staged or activated.

Private candidate DMG SHA-256:
`dbebfe403f3a95ef1c363511ee12b86f6f096a3ef6bdae5b43dd28858d1815dd`.
Disk-image, mounted bundle/platform, ad-hoc signature and frozen offline smoke
checks pass. All **30 frozen application modules** and the entrypoint in the
mounted DMG match the exact committed source. This private DMG is not acceptance
of a future CI installer.

## Checks

- Frontend: formatting, TypeScript, **477 tests** and production build with
  CI-pinned Node **22.23.2**.
- Service/contracts: Python **3.11.17**, Ruff lint/format and **310 tests**, no skips.
- macOS native: Rust **1.98.1** formatting, strict Clippy, **98 tests** and debug build.
- Release tools: **166 tests**, script Ruff lint/format, version plan and pinned
  **actionlint 1.7.7** against both workflows.
- Private frozen smoke: health, vertical OCR geometry, Lindera, JMdict, KANJIDIC2,
  optional translation and saved-data/cache persistence across restart.

Official downloaded tool archives were checksum-verified. Logs and machine-readable
results remain in the ignored preparation directories. The existing frontend
large-chunk advisory remains. Windows hosted Checks and exact CI installers are
separate from these local macOS checks.

## Remaining gates

The owner must review and approve the exact source/licence delivery before a
source-approved seed is built, verified and privately activated. The previous
seed approval does not extend to `2059ccb`. Follow the
[seed procedure](release-runbook.md#build-a-replacement-macos-seed), keeping the
unsigned worksheet and actual approval separate. Merge only when authorized,
with current PR Checks passing and the reviewed source history preserved.

Release waits for successful Checks on the exact main merge, selects the compatible
reviewed seed, builds both installers and verifies the complete delivery. Both
exact CI installers then require hash-bound acceptance and separate owner approval
of the protected `desktop-release` deployment. No main merge, release dispatch,
public tag or publication approval is claimed here.

Fresh-Mac/Gatekeeper/Screen Recording, live native Auto detect, Windows hardware,
mixed-DPI/IME interaction, real-manga accuracy and full filtered-source-only rebuild
limits retain their recorded scope. Dated dependency advisories are not revalidated
by this preparation. macOS remains ad-hoc signed and unnotarized.
