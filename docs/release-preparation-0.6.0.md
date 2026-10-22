# v0.6.0 release preparation — 2026-10-22

Version **0.6.0** is a pre-release under the existing version policy.
Branch `release/0.6.0` starts from main `044cf8a`; version commit
`194dd5704b2a07c5f57c380f60adac35c748e46d` updates all five npm/Tauri/Cargo
app version files together. Dependency versions, model/dictionary pins and
release workflows are unchanged.

## Source and release notes

The previous published app tag is `v0.5.0`, source
`8ff3be2621096a9804cc23ba33902f5aab34da55`. GitHub's unsaved release form,
targeting this release branch and explicitly comparing with `v0.5.0`, generates
PRs **#28–#37**: publication and seed workflow repairs, detector setup link,
OCR hiding, interrupted selection handling, horizontal and mixed-content
geometry recovery, theme/icons, tray restoration and the final UI redesign.

The PR inventory was checked against the final source and CHANGELOG. Intermediate
muted button colors and dark OCR halos were superseded; current UI uses
`#0080FF` blue and the final popup layout. Historical CHANGELOG entries remain
intact. Public notes contain only the generated PR list followed by
[Full Changelog](https://github.com/chonnakanch/yomimado/compare/v0.5.0...v0.6.0).

The local GitHub CLI is unavailable, so the preview uses the signed-in GitHub UI
without saving a draft or creating a tag. Its transcribed Markdown and explicit
UI provenance are retained in the ignored seed work directory. CI will generate
and hash-bind its own preview to the exact main merge, including this release
PR, before the protected publication review.

## Runtime seed boundary

The reviewed seed source remains `46a5649007caf09538adb7d7d0bc4bda763c095e`.
It cannot supply this release's frozen Python service: `geometry.py` and
`real_ocr.py` changed. The strict reuse guard also rejects changed app icons.
No allowlist or seed pin was widened. Ordinary PR Checks can pass while Release
correctly refuses an incompatible seed.

A new private runtime candidate is prepared at version source `194dd57`.
The generated dependency and native inventories are byte-identical to the
previous seed. All 29 frozen application modules and the packaged entrypoint
match this exact committed source. The private DMG passes mounted bundle/platform
validation and offline frozen health, vertical OCR geometry, Lindera, JMdict,
KANJIDIC2, optional translation and saved-data/cache restart smoke checks.

The ignored local work directory is
`services/ocr/build/runtime-seed-194dd57/`. Its unsigned source delivery
`source-delivery-194dd57/` covers **476 component/native records**, **76 archives**
and **112 unique native inputs**, with no missing source/notice references.
All 75 retained original dependency archives are hash-verified. Independent
comparison checks **163,811 retained files** across 107 containers and all
**2,347 documented asset/vendor-map changes**, with no code or notice changes
introduced by filtering. The exact project export includes the current app
icons, runtime source, locks and required source/build records.

Unsigned worksheet SHA-256:
`5b7b908d14295f357396564dedfd8b39553baaf69c93c356faaecfe73fa06235`.
Private test DMG SHA-256:
`a6569f7ad031629afcaf831ee3139335fa9d5c81139997e4ab4c21fc6a2ada4c`.
The mounted DMG's 29 frozen modules and packaged entrypoint independently match
the exact source. `REVIEW.md`, structural/content reports, source-preparation and
mounted module comparison are retained beside/inside that delivery.

The owner subsequently approved this exact source/licence delivery and private
seed activation on **2026-10-22**. The original unsigned worksheet remains intact;
the actual decision and approved manifest are recorded separately. The
source-approved DMG has its own hash, distinct from the earlier private test
DMG above. The [seed record](macos-runtime-seed.md#v060-replacement-seed--2026-10-22)
retains its exact four input hashes/sizes, approval hash, private draft and
owner-uploaded activation manifest. Source-only rebuilding and the dated
dependency advisory review remain unverified; unchanged inventories do not
resolve those earlier limits.

## Local verification

- Frontend: formatting, TypeScript, **324 tests** and production build, using
  CI-pinned Node **22.23.2**. The downloaded official runtime checksum verifies.
- Service/contracts: Python **3.11.17**, Ruff lint/format and **243 tests**, no skips.
- macOS native: Rust **1.98.1** formatting, strict Clippy, **80 tests** and debug build.
- Release tools: **166 tests** across publisher, release rules, seed selection,
  version updater, PR notes, JLPT provenance and macOS source/notices/release checks.
- Script Ruff lint/format and both workflows' pinned actionlint pass.
- Version plan: `0.6.0`, tag `v0.6.0`, `prerelease=true`.

[PR #38](https://github.com/chonnakanch/yomimado/pull/38) at `9f3d290` passes all
six hosted Checks in [run 39786713459](https://github.com/chonnakanch/yomimado/actions/runs/39786713459),
including macOS and Windows native jobs. Documentation follow-ups require their
own current-head Checks; these source checks do not establish Windows hardware
or exact-installer acceptance.

Initial local test attempts used obsolete Python 3.9 and installed Node 26;
their environment failures were resolved by using the pinned supported tools.
The frontend retains the existing large-chunk build advisory. Private DMG creation
and mounting require host access beyond the sandbox; the successful candidate
uses the unchanged build recipe and ad-hoc signing.

## Remaining release gates

The replacement runtime seed is owner-approved and activated privately. Merge with
commit history preserved so reviewed source `194dd57` remains an ancestor.
Release then requires successful Checks on the exact main merge and dynamically
selects the compatible owner-approved seed. A fresh Release run can discover a
newly activated seed after an early compatibility failure.

The private candidate is not acceptance of the future CI installers. Both exact
CI installers need hash-bound testing and the owner's separate protected
`desktop-release` publication approval. Keep main at the candidate source through
publication. Fresh-Mac waivers, Windows hardware limits, real-manga accuracy,
native WebKit/IME interaction and complete filtered-source-only rebuilding retain
their recorded scope. macOS remains ad-hoc signed and unnotarized.
