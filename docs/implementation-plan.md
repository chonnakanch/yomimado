# YomiMado — Implementation Plan

## Current status

Updated **2026-10-13**. Current work is post-release maintenance on tracked
`develop`; the app version remains `0.1.0`.

The **first desktop pre-release milestone is complete**.
[YomiMado v0.1.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
was published on 2026-10-12 for macOS Apple Silicon and Windows 11 x64 CPU.
Both exact-hash local installer reports and protected owner publication pass.
The maintainer is satisfied with the current app; no further v0.1.0 testing or
UI implementation is requested.

The tag remains at tested app source
`5159473da21c952f1a4dc87c457bba82edf5edde`. Recovery executor
`a30d0ba2b931ab9443b656b64ed55ba7a1d9ffc0` published the existing delivery after
owner approval, without rebuilding or replacing installers or moving the tag.
The [shared release record](desktop-release.md) retains build/recovery URLs,
original delivery identities, uploaded-hash verification and owner reports.

The workflow/script cleanup, version updater, code-quality fixes (`973c721`) and
security fixes (`8c8ef02`) are committed on `develop`. They have not been delivered
to v0.1.0 users. The next release requires updated runtime inputs and a newly
reviewed macOS seed; the original frozen runtime cannot include these shared
Python changes. Keep the existing seed-reuse rejection checks in place.

| Published installer     | SHA-256                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| Windows x64 setup       | `a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602` |
| macOS Apple Silicon DMG | `9d2999ae49b1756d23e62e6b703284e1d5c87898dc187757dfa3d881b8b28977` |

## Completed application scope

- [x] Tauri 2 desktop with React/TypeScript and Rust capture/process integration.
- [x] Manual capture selection, global shortcuts and reusable manga scan area.
- [x] Local horizontal/vertical OCR with geometry preserved through the service API.
- [x] Explicit physical-pixel/image/logical coordinate transforms and interactive overlay.
- [x] Windows overlay alignment and clicking verified at 100%, 125% and 150%.
- [x] On-demand Sudachi word analysis, local JMdict lookup and KANJIDIC2 details/compounds.
- [x] On-demand local Japanese-to-English translation with caching.
- [x] Explicit word/sentence saving and viewing, local persistence after restart/reboot.
- [x] Optional estimated reading-order controls; no complete panel reconstruction.
- [x] User-installed detector ONNX import with checksum checks; weights never bundled.
- [x] Sources/licences available in the app; original manga stays visible and screenshots local.

OCR providers remain behind the local API boundary. Recognition confidence is
unknown; approximate regions are marked for review. Translation, dictionary data,
software and model terms remain separate concerns. Do not expand to Linux/mobile,
continuous OCR, automatic translation or image text replacement without a new request.

## Completed release scope and retained limits

- [x] macOS Apple Silicon DMG with reviewed frozen runtime, mounted verification,
      source/notices delivery and existing-Mac installed acceptance.
- [x] Windows 11 x64 per-user NSIS setup with source-built CPython, CPU ONNX inference,
      hidden-console startup, resource/data paths and process cleanup.
- [x] Actual Windows native inputs and sources/notices reviewed independently of macOS.
- [x] Windows runtime requires no developer Python/CUDA and delivers no Torch/MKL/IPP.
      Export/reference packages remain separate from installed inference.
- [x] Owner Community 2022 acquired-copy/terms confirmation, component-only installer
      terms and acceptance/rejection verification recorded.
- [x] Browser/security, model/buttons/shortcuts, offline learning, persistence,
      scaling and upgrade/uninstall/reinstall groups pass for the published Windows hash.
- [x] One shared version tag/publisher, protected main and separate owner publication review.
- [x] All 17 v0.1.0 uploaded assets verify; the existing public delivery is preserved.

The Windows PC is confirmed x64: Windows 11 Home 25H2 build 26200.9457,
Core i5-14500, 32 GB RAM and a 2560 × 1440 display. AMD, additional/mixed-scale/
left-of-primary monitors, clean-machine missing-WebView2 and unreported detailed
cases remain untested. Fresh-Mac testing is waived; the existing-Mac report passes.
The DMG is unnotarized/ad-hoc signed and Windows setup is unsigned hobby distribution.
Full source-only rebuilding of the complete delivery remains unverified.
See [Windows](windows-installed-test.md) and [macOS](macos-clean-mac-test.md) reports.

## Completed post-release maintenance

- [x] Simplify active workflows to [Checks](../.github/workflows/checks.yml) and
      [Release](../.github/workflows/release.yml). Checks retains the required `gates`
      job; Release builds both platforms and waits for protected owner approval.
- [x] Retire standalone audits, the separate Windows private candidate and one-time
      recovery workflow. Remove obsolete experiment/recovery tools while retaining
      live build helpers and required source/licence evidence.
- [x] Prepare six-file future release delivery: both installers, combined source/data/
      recipe archive, combined notices/records archive, checksums and provenance.
      Preserve every original input and verify nested hashes, member safety and size.
- [x] Remove superseded documentation drafts/timelines/workflow copies and fix references.
- [x] Review script dependencies, remove one-time recovery/private experiment tools
      and retire unused develop-only staging/download commands; preserve live
      runtime, build, source/notice and native replacement helpers.
- [x] Rename shared release API/dictionary helpers and Windows ONNX preparation,
      export, verification and runtime scripts to describe their current functions;
      update callers, imports, source recipes and exporter provenance checks.
- [x] Add a documented version-update command for npm/Tauri/Cargo metadata and
      app lock entries, with preview, input validation and dependency preservation.
      [Usage](../scripts/README.md#update-the-app-version) covers all five files;
      Checks now also runs the updater's regression tests.
- [x] Rename the shared release-rule suite to `test_release_rules.py` and update
      Checks and review references; retain its macOS runtime-reuse checks.
- [x] Complete a focused [code quality review](code-review-2026-10-13.md): share
      frontend transport/token validation, validate OCR responses, remove repeated
      popup resets and fix stale translation responses/cache cleanup. Shared Python
      changes require a newly reviewed macOS runtime seed for a future release.
- [x] Complete a focused [security review](security-review-2026-10-13.md): reject
      hostile browser requests, bound uploads/decoded dimensions, narrow frontend
      environment exposure and update vulnerable npm development tooling. Record
      remaining frozen-runtime advisories without changing tested v0.1.0 inputs.

Recorded local verification for the latest source changes: 100 frontend tests,
TypeScript and production build; 78 OCR service tests across the applicable
Python interpreters; 36 Rust tests and a macOS debug build. The three required
release/version suites pass 51 tests. See the dated reviews for exact interpreter
coverage and limitations. These checks do not establish installed acceptance of
the new code; no new Windows installer was built for those reviews.

## Next milestone: refreshed runtimes and next release

The remaining release prerequisite is the runtime refresh recorded in the
[security review](security-review-2026-10-13.md). Its dated advisory snapshot
matches 13 distinct Python package names across the macOS/Windows inventories.
Installed inference, export/reference packages and build tools need separate
reachability and licensing review. Prioritize Starlette and python-multipart's
request/form parsing paths; the new origin/size guards do not patch dependencies.

Proceed in this order when continuing release preparation:

1. [ ] Extend required [Checks](../.github/workflows/checks.yml) to run frontend
       and OCR service regression tests, plus their lint/type/format checks. Use Python
       3.11 or later for Windows graph-checksum tests; currently only the three
       release/version suites run in this workflow.
2. [ ] Triage the recorded Python advisories and choose compatible patched exact
       inputs for both platforms. Update locks, hashes, preferred sources, recipes
       and licence/native notices together; preserve historical delivery records.
3. [ ] Build and verify refreshed runtimes containing the shared translation and
       security fixes. Prepare and review a new macOS seed, then update its pinned
       identity and source bindings. Verify the Windows CPU ONNX path, hidden-console
       lifecycle and model exclusion with the updated inputs. Keep long Torch source
       builds out of the normal release flow.
4. [ ] Choose the next app version and apply it with
       [update_version.py](../scripts/update_version.py). Review the five-file diff
       and run relevant app/native/service/release checks before an authorized PR
       merge through protected `main`.
5. [ ] Let [Release](../.github/workflows/release.yml) build both new installers
       and verify the real six-file candidate: source/data/recipe and notice archives,
       nested hashes, provenance, architecture, native dependencies and upload size.
       Confirm that the renamed Windows backend modules are collected by the freezer.
6. [ ] Record local acceptance for both exact new installer hashes, including
       Windows 100%/125%/150% scaling, offline learning, persistence and upgrade/
       uninstall. Retain untested hardware cases and any explicit macOS waiver.
       The owner supplies protected publication approval after these gates pass.

There is no version bump, main merge or publication in this plan update. The
published v0.1.0 needs no further testing. A released version is skipped by the
main workflow. Future `0.x.x` and `alpha.N`/`beta.N`/`rc.N` versions are pre-releases;
`1.0.0` and later without a suffix are stable. Both classifications retain the
same exact-installer publication gate.

## Deferred maintenance

These review follow-ups are recorded separately from completed fixes:

- [ ] Decide whether to add per-launch local service authentication and an
      inference admission/concurrency limit. The current client header guards
      browser requests; other native processes can still supply it.
- [ ] Track the Rust maintenance advisories and supported-platform reachability
      recorded in the security review; update reviewed inputs when applicable.
- [ ] Consider the code review's native capture helpers, shared smoke-request
      helper and smaller popup/pipeline functions when changing those areas.
      Preserve coordinate behavior and platform verification.

## Optional post-release UI discussion

The earlier redesign idea remains a discussion only. The maintainer currently
wants to keep the app as it is. If requested later:

1. Review the main window, capture flow, overlay and learning popups together.
2. Agree goals and visual direction before mockups or implementation.
3. Discuss a Jisho-inspired popup with prominent word/reading, grouped meanings
   and compact kanji meanings/on/kun details; use inspiration rather than an exact copy.
4. Support smaller screens with stacked sections and scrolling; omit Wikipedia.
5. Consider common-word/JLPT tags only with suitable attributed data; never invent levels.

Older per-attempt plans and abandoned experiments remain recoverable in Git at
`2885586`. Current build inputs, software/data terms, exact release records and
replacement recipes stay in the repository; use the [documentation index](README.md).
