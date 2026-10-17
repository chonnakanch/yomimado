# YomiMado — Implementation Plan

## Current status

**SudachiPy investigation — 2026-10-17:** confirms the current baseline is already
Rust-backed SudachiPy 0.6.10. A same-corpus 39-sentence benchmark adds hash-verified
Sudachi Small 20250515: 117.25 MiB versus Core's 207.06 MiB and Lindera's 45.33 MiB;
focused learning checks pass 7/8, 8/8 and 7/8 respectively. Small differs from
Core on ten sentences; Lindera differs on twenty. All source offsets pass.
The [report](sudachipy-investigation.md) separates tokenizer quality from image
OCR, records newer-version compatibility and keeps the production default.
Only the benchmark and documentation change; release inputs remain unchanged.

**Scan performance comparison — 2026-10-17:** 90 synthetic CPU scans return
identical OCR text/geometry with Sudachi and Lindera. Median service scan times
are 836/840 ms; the mixed page takes 4.37/4.53 seconds with five detector passes.
Both share seven exact pipeline strings out of ten, 9.3% character error rate
and the short-kana/low-contrast failures; supplied true-crop recognition is
10/10 exact. The [report](scan-performance-comparison.md) separates detector,
recognizer and learning quality and discloses the small synthetic scope. Seven
metric tests pass. This adds benchmark/evidence only; production OCR, runtime
inputs and installer acceptance are unchanged.

**Lindera development launch repair — 2026-10-17:** the tokenizer-only service
example omitted OCR model paths, so page scanning received the demo engine and
rejected it. `scripts/dev_lindera_service.py` now resolves existing local OCR,
Lindera and learning assets independently of the terminal directory, checks the
required paths and starts the full development service. Three launcher tests
and a temporary-port real HTTP smoke pass horizontal/vertical OCR geometry,
tokenization, word/kanji lookup and local translation. The
[experiment guide](lindera-tokenizer-experiment.md) contains the corrected command.
No packaged runtime, release input or installer evidence is changed.

**Lindera development experiment — 2026-10-17:** branch
`codex/lindera-tokenizer-experiment` adds an opt-in, hash-pinned Lindera 6.0.0/IPADIC
adapter. Its 45.33 MiB dictionary saves 161.73 MiB versus Sudachi Core, before
native package costs. Source offsets pass over 39 sentences; 20 have different
words/readings/base forms. Lindera passes seven of eight focused learning checks
versus Sudachi's eight; strict parity fails on the whole-word `お兄ちゃん` case.
All 110 service tests, a 100-request concurrent native HTTP smoke and the frontend
production build pass. See the [experiment](lindera-tokenizer-experiment.md).
Sudachi remains the default. Release locks, reviewed runtime seeds and installer
evidence are unchanged; Windows/frozen-service and release-source review remain.

**Tokenizer resource investigation — 2026-10-17:** an isolated source probe
preserves the 6,144-entry OCR vocabulary, 12,804 decoding cases, ten synthetic
recognitions, tokenizer serialization and Sudachi learning analysis without
UniDic/Fugashi imports. Sudachi Small `20250515` saves 89.81 MiB versus Core's
dictionary but changes ten of 32 analyzed sentences, including `お兄ちゃん`.
The [investigation](tokenizer-resource-investigation.md) recommends keeping Core
and pursuing removal of the approximately 248.4 MiB UniDic dependency from OCR.
Production code, dependency locks, runtime seeds and installer evidence are
unchanged. Frozen services and native Windows ONNX parity remain unverified;
this investigation does not complete a packaging/release milestone.

**0.2.2 packaging repair — 2026-10-17:** [PR #12](https://github.com/chonnakanch/yomimado/pull/12)
merged at `32b5117`, with all source gates passing. The macOS installer passes,
but Windows packaging stops at a GitHub API rate limit while collecting three
already pinned vcpkg port files. The repair uses commit-pinned raw downloads of
the identical bytes/hashes, retains the old blob URLs and adds corruption/cache
regressions. Both new installers and their combined verification must run again
from the repaired main commit. The [release record](desktop-release.md) retains
the failed run and superseded macOS candidate without claiming acceptance.

**0.2.2 release preparation — 2026-10-17:** the owner requested release of the
tray work as `0.2.2`. The version updater changes the five app metadata files;
release notes include the tray controls, Windows manifest repair and taskbar
exclusion. The native-only reuse preflight adjustment retains the approved
frozen OCR runtime and exact dependency sources/notices. Protected-main checks,
both new installers and exact-installer acceptance/publication follow the
[shared release checklist](desktop-release.md). Historical installer hashes and
reports are preserved.

**System tray source implementation — 2026-10-17:** the owner authorized the
[system tray plan](system-tray-plan.md). Native macOS menu bar / Windows tray
integration now provides toolbar show/hide, Saved/settings/sources access and
shared Quit cleanup. Windows left-click restores the toolbar; right-click opens
the menu. Capture guards prevent window actions while a scan is active. A tray
startup failure keeps the toolbar available and reports an error. Dedicated
icons, a reproducible generator and a [license review](../THIRD_PARTY_LICENSES/system-tray-review.md)
are included; dependency versions and the app version are unchanged.

Local verification passes 70 native tests, 177 frontend tests, strict Clippy,
Cargo/Prettier/Ruff formatting and the macOS debug app bundle build. The macOS
debug smoke confirms toolbar launch, the Hide Toolbar action/hint, hiding and
normal OS Quit; the UI automation surface did not expose the native status item
for menu-click/restore checks. Full native tray interaction, appearance/scaling,
Explorer restart and bundled service cleanup still need platform acceptance.
Existing candidate hashes and acceptance records are unchanged; no new installer
has been built or approved by this source work.

The first hosted tray run passed macOS/frontend/service/release-tool checks but
Windows unit-test startup failed with `STATUS_ENTRYPOINT_NOT_FOUND`. The source
repair embeds the Common Controls v6 manifest in tests as well as app binaries;
the app retains the equivalent default dependency. See the tray plan for the
upstream diagnosis and remaining native acceptance.

Hosted [Checks run `38995496517`](https://github.com/chonnakanch/yomimado/actions/runs/38995496517)
passes for repaired source `74bb75e`: frontend, service, release tools, macOS and
Windows native lint/tests/debug builds, Windows synthetic UI-driver checks and
the required shared gate. This confirms the Windows test-startup repair; the
native tray acceptance limits above remain open.

**Windows taskbar follow-up — 2026-10-17:** after accepting the 0.2.1 overlay
startup repair, the owner reported automatic manga detection including the
Windows taskbar. The source follow-up restricts both Windows automatic entry
points to the selected monitor's OS-reported work area before page detection and
OCR. It preserves full-monitor physical/logical coordinate mapping and exact
manual selections. This follow-up is separate from the already built and tested
`31f51a7` candidate; that candidate's hashes and acceptance are unchanged.

Local verification passes 65 native tests, the 22 capture-selector frontend
tests, strict Clippy, Cargo/document formatting and the macOS debug build.
Regression coverage checks bottom/top/left/right taskbar work-area insets,
100%, 125%, 150% and 200% scales, negative/secondary monitor origins, unchanged
full work areas and invalid-area rejection. Windows-specific compilation and
physical taskbar exclusion require Windows checks; no new installer is built or
accepted by these local results.

**0.2.1 candidate update — 2026-10-17:** the Windows missing-overlay startup repair
merged through [PR #11](https://github.com/chonnakanch/yomimado/pull/11) at
`31f51a7c4fe1bb192c3eeecea1f90d57d3ee5882`. All exact-main Checks, both installer
builds and combined verification pass. The [verified candidate](https://github.com/chonnakanch/yomimado/actions/runs/38930205981/artifacts/12060264675)
has an owner-reported Windows pass: **“Both modes and keyboard work”** after the
fresh-launch Whole Screen, Selected Area and Read with keyboard → Enter check.
This confirms the missing-overlay repair on the owner's setup; mixed-DPI and
other hardware coverage remain open. The protected `desktop-release` publisher waits
for separate approval; v0.2.0 remains published. See the
[release record](desktop-release.md) for hashes, download lifetime and limits.

Updated **2026-10-16**. The owner closed the UI redesign implementation on tracked
`develop`, through source commit `cd2d202`. Phases 3, 4 and 5 retain their recorded
approvals. The owner subsequently authorized version `0.2.0`, integration into
`main` and a release build. Protected [PR #7](https://github.com/chonnakanch/yomimado/pull/7)
merged at `645ba088118f41880abfc37df1b595fa85e3ad42` after all required checks
passed. The [0.2.0 installer build](https://github.com/chonnakanch/yomimado/actions/runs/38841492110)
ran from that exact main commit; the macOS candidate passed, but the Windows
installed-startup check exposed a UI Automation driver mismatch. The repair passed
all checks and merged through [PR #8](https://github.com/chonnakanch/yomimado/pull/8),
then [PR #9](https://github.com/chonnakanch/yomimado/pull/9) added Toggle-only scan
coverage. Release source is `c03ee1edba4e0f545cb7ed85a7552c544a4bfcdc`; its
[build](https://github.com/chonnakanch/yomimado/actions/runs/38892964547) passes both
installers and combined verification. The protected publisher subsequently passed
after owner approval; [v0.2.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.2.0)
was published as a pre-release on 2026-10-16 at 19:22 Bangkok time.
All main source CI gates pass. Remaining
native-platform verification and packaging are separate release-preparation work;
closing implementation does not approve installers or publication.

The **first desktop pre-release milestone is complete**.
[YomiMado v0.1.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
was published on 2026-10-12 for macOS Apple Silicon and Windows 11 x64 CPU.
Both exact-hash local installer reports and protected owner publication pass.
The maintainer is satisfied with the published app; no further v0.1.0 testing
is requested. The new UI redesign approval below applies to source development
for future delivery and does not alter historical installer acceptance.

Availability update — 2026-10-13: after deleting the original tag, the owner
merged [PR #6](https://github.com/chonnakanch/yomimado/pull/6) at
`b188b05dd42ac5553cfbc0c1188c9646e2ce29ca`. Main Checks and
[Release `38378686892`](https://github.com/chonnakanch/yomimado/actions/runs/38378686892)
pass, including both builds, combined verification and protected publication.
Public v0.1.0 downloads are available again with six uploaded files and new
installer bytes. Their public API hashes, exact tag/source and downloaded
provenance/checksum records verify. Local acceptance for these new hashes is not
recorded; the previous human passes are preserved for their original installers.

The original tag pointed at tested app source
`5159473da21c952f1a4dc87c457bba82edf5edde`. Recovery executor
`a30d0ba2b931ab9443b656b64ed55ba7a1d9ffc0` published the existing delivery after
owner approval, without rebuilding or replacing installers or moving the tag.
The [shared release record](desktop-release.md) retains build/recovery URLs,
original delivery identities, uploaded-hash verification and owner reports.

The workflow/script cleanup, version updater, code-quality fixes (`973c721`) and
security fixes (`8c8ef02`) are merged through PR #5 and delivered by the October 13
republication. The [refreshed macOS seed](macos-runtime-seed.md) now contains
the shared Python fixes and has source-only owner approval; dependency versions
are unchanged. Advisory triage and new exact-installer gates remain open.
Keep the existing seed-reuse rejection checks in place.

| Original October 12 installer | SHA-256                                                            |
| ----------------------------- | ------------------------------------------------------------------ |
| Windows x64 setup             | `a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602` |
| macOS Apple Silicon DMG       | `9d2999ae49b1756d23e62e6b703284e1d5c87898dc187757dfa3d881b8b28977` |

| Current October 13 installer | SHA-256                                                            |
| ---------------------------- | ------------------------------------------------------------------ |
| Windows x64 setup            | `61bbd7aefa46d895c1afae9d549e0d357d364bc647341d32ef08fe0957f74b59` |
| macOS Apple Silicon DMG      | `1d6cadbff7e454d09c790bc002b259ea0f8a2997392e6034bda8f9cb698df462` |

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
- [x] Expand Checks into parallel frontend, service, release-tool and macOS/Windows
      native jobs. Preserve required `gates`, reject skipped service tests and all
      non-success job results, pin test inputs and cache repeated work.
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

CI follow-up — 2026-10-13: a fresh Python 3.11.17 test environment runs all 78
service cases without skips and the 51 release/version cases. Frontend tests,
type/format checks and production build pass; macOS native tests/build pass.
The final gate rejects all 624 failing/cancelled/skipped/missing-result combinations
and accepts the one all-success combination. Linux wheel resolution and original
CI-tool notice hashes verify. Hosted
[Checks run `38345712285`](https://github.com/chonnakanch/yomimado/actions/runs/38345712285)
passes every job, including Windows and macOS native tests/builds;
this follow-up changes no frozen runtime or installed-app acceptance record.

## Next maintenance: dependency refresh and future versions

The remaining dependency maintenance is recorded in the
[security review](security-review-2026-10-13.md). Its dated advisory snapshot
matches 13 distinct Python package names across the macOS/Windows inventories.
Installed inference, export/reference packages and build tools need separate
reachability and licensing review. Prioritize Starlette and python-multipart's
request/form parsing paths; the new origin/size guards do not patch dependencies.

Proceed in this order when continuing release preparation:

1. [x] Extend required [Checks](../.github/workflows/checks.yml) with frontend and
       OCR service regression tests, lint/type/format checks and native verification
       on both desktop platforms. Python uses 3.11.17; the original three release/
       version suites remain. The final `gates` requires all parallel jobs to pass.
2. [ ] Triage the recorded Python advisories and choose compatible patched exact
       inputs for both platforms. Update locks, hashes, preferred sources, recipes
       and licence/native notices together; preserve historical delivery records.
3. [x] Build and verify refreshed runtimes containing the shared translation and
       security fixes. Prepare and review a new macOS seed, then update its pinned
       identity and source bindings. Verify the Windows CPU ONNX path, hidden-console
       lifecycle and model exclusion with the updated inputs. Keep long Torch source
       builds out of the normal release flow.
4. [ ] Choose the next app version and apply it with
       [update_version.py](../scripts/update_version.py). Review the five-file diff
       and run relevant app/native/service/release checks before an authorized PR
       merge through protected `main`.
5. [x] Let [Release](../.github/workflows/release.yml) build both new installers
       and verify the real six-file candidate: source/data/recipe and notice archives,
       nested hashes, provenance, architecture, native dependencies and upload size.
       Confirm that the renamed Windows backend modules are collected by the freezer.
       Run `38378686892` passes the real six-file candidate and publication.
6. [ ] Record local acceptance for both exact new installer hashes, including
       Windows 100%/125%/150% scaling, offline learning, persistence and upgrade/
       uninstall. Retain untested hardware cases and any explicit macOS waiver.
       Protected publication has completed, but no new local acceptance report
       for the October 13 hashes has been received in this chat. The owner requests
       no additional current-release testing; do not infer a pass or a new waiver.

The owner merged the cleanup in PR #5 and the verified inputs in PR #6 through
protected main. The app version remains unchanged; publication followed through
the protected release job. The original October 12 v0.1.0 acceptance needs
no further testing. A published version with its tag is skipped; a missing tag
requires runtime compatibility before private downloads or builds. The new
`42edd4e` seed passes the source/runtime gates.
The owner has now uploaded all four private input files. The API uploader's
success report and independent browser inspection confirm draft/source identity
and every GitHub SHA-256. The repacked Windows archive retains the exact pinned
dictionary gzip files. Both input pin sets are integrated on protected main; exact
membership/hash checks, dictionary restoration and macOS runtime-reuse preflight
pass. Forty-six release/rule/dictionary tests, lint/format and actionlint pass.
The web-upload blocker is resolved through the owner-run API recovery. All 12
PR #6 checks and the main Checks/Release jobs pass. Neither seed draft is public;
the new public installers have separate hashes and no local acceptance record.
See the [verified seed record](macos-runtime-seed.md).
Future `0.x.x` and `alpha.N`/`beta.N`/`rc.N` versions are pre-releases;
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

## UI redesign — Phase 1 review

The owner approved [the redesign plan](ui-redesign-plan.md) and
[design system](design-system.md) on 2026-10-13, and authorized design tokens and
the floating toolbar only. **Phase 1 was approved for continuation; Phase 2 is implemented for source/result review.**

- [x] Semantic CSS palette, typography/spacing/shape tokens, readable controls,
      focus indicators, offline native font fallback and transparent utility roots.
- [x] Separate always-on-top draggable toolbar; collapsed native bounds, saved
      collapse preference, keyboard movement and accessible overflow navigation.
- [x] Selected Area, Whole Screen, fresh-pixel Rescan and reversible result visibility.
      Monitor-bound session state, busy/cancel/errors and stale-response protection.
- [x] Keep secondary main window hidden on startup and alive after close; existing
      saved collections, detector import, sources/notices and Quit remain accessible.
- [x] Preserve local OCR/dictionary/tokenization/translation/persistence and developer
      capture diagnostics. No service/dependency/data/license/version changes.
- [x] Owner approval to continue beyond Phase 1.
- [x] Owner authorized the Compact dictionary popup phase on 2026-10-14.
- [x] Saved-collection layouts implemented after owner authorization to continue
      Phase 4; result acceptance is tracked below.
- [x] Owner accepted Phase 4 and authorized the Settings phase on 2026-10-14.

Local verification: 113 frontend tests in 19 files, TypeScript, Prettier and
production Vite build; 44 native Rust tests, Rust formatting and macOS debug
build; all 78 service cases under pinned Python 3.11.17. Token text/action/focus
contrast pairs were measured. The older Python 3.9 environment initially passes
77 cases and fails the existing `hashlib.file_digest` Windows graph case; the
pinned CI interpreter passes all cases without service changes.

macOS debug UI smoke checks: toolbar-only startup, 520 × 56 / 112 × 48 logical
window bounds, collapse/expand, drag, menu access, secondary-window close/reopen,
permission-error recovery and Quit. The temporary debug bundle lacks Screen
Recording permission; no OS settings were changed. Successful native capture,
Rescan and hide/show, Windows UI behavior and mixed-DPI/multiple-monitor runtime
checks remain unverified. Geometry/admission/cancellation tests pass, but do not
substitute for those native interactions. This is not installed-app acceptance;
no installer/tag/publication or historical v0.1.0 evidence was changed.

Older per-attempt plans and abandoned experiments remain recoverable in Git at
`2885586`. Current build inputs, software/data terms, exact release records and
replacement recipes stay in the repository; use the [documentation index](README.md).

## UI redesign — Phase 2 review

The owner authorized the next phase after the toolbar and tokens. Phase 2 covers
OCR region visuals and native input routing, before the dictionary popup redesign.
The owner selected **Compact popup** in the visual preview for that later phase.

- [x] Extract `OCRBoundingBox` and scoped overlay styles. Preserve original polygons,
      physical/logical transforms and vertical text; default orange, hover orange,
      selected blue, dashed review/approximate/demo cues and explicit accessible labels.
- [x] Native Windows polygon/controls window region; macOS native cursor sampling
      plus mouse-ignore toggling (8 ms active, 80 ms idle), with drag ownership retained.
      Disable hit routing on capture, hide and close; fresh reveal generations replace
      old geometry. Quartz also fixes the observed Retina shortcut monitor-targeting
      failure in the pinned Tao cursor path. No mouse-event replay, new platform
      permission or dependency.
- [x] Toolbar **Focus regions**, roving region focus, arrows/Home/End, Enter/Space;
      Escape hides results while retaining them. Keyboard-origin popup dismissal returns
      to the selected region; blur dismissal leaves focus with the reader.
- [x] Keep estimated reading-order navigation optional; measure only its actual control
      bounds for native input. Review guidance is passed to the existing learning popup.
      Dictionary, translation, corrections and persistence are otherwise unchanged.
- [x] Synthetic local reader fixture for native verification, excluded from the production
      build. See [the native UI checks](ui-overlay-testing.md).
- [ ] Complete native acceptance on Windows and mixed-DPI/multiple-monitor systems.
- [x] Owner authorized continuation to the Compact popup after toolbar acceptance
      on 2026-10-14; remaining Windows/mixed-DPI runtime evidence is still tracked.

Source checks: **117 frontend tests in 19 files**, TypeScript/production Vite build,
Prettier, **49 native tests**, Cargo formatting and macOS debug build. Service code,
dependencies, data contracts, version and release records are unchanged.

[Checks run 38502525855](https://github.com/chonnakanch/yomimado/actions/runs/38502525855)
passed every gate for implementation commit `7190630`: frontend, service,
release-tools, macOS native tests/build and Windows native tests/build. The
Windows native build is verified by CI; Windows interactive acceptance is still open.

Runtime verification on 2026-10-14: the owner confirmed Whole Screen produced a real
OCR overlay using the normal `tauri dev` command and existing offline models. Native
logs recorded a complete 2940 × 1912 physical capture and `manga` result. Earlier
Phase 1 debug testing passed Selected Area, repeat capture and same-generation
hide/show with the demo boundary. Ad-hoc app grants were tied to executable hashes;
normal command-based development avoided the temporary bundle grant problem.

The first command session ended before repeatable input/CPU measurements could be
confirmed. Although Safari scrolling/clicking/text selection was observed, this alone
is not accepted as proof that the native overlay was still active. A detached normal
development process is running for final checks. Its root-process idle sample was
0.0% CPU; a later sample was 2.0%. These snapshots include the app UI and do not
isolate sampler cost or establish a performance guarantee. The owner subsequently
confirmed region keyboard entry, arrow navigation, popup dismissal/focus return,
quick region clicks and Hide/Show work in the running development app. This is a
functional smoke check, not a measured fast-entry click-loss or latency benchmark.
Polling latency/CPU and Windows native behavior remain acceptance gates.

The owner reported missing outlines in Selected Area mode. Opt-in development
geometry diagnostics reproduced a reused-window frame shift: resizing from 1794
physical pixels tall to 1442 after setting its position moved its top from 289 to
642, clipping the upper text even though all three OCR polygons were present.
Establish the target monitor, resize the hidden overlay, then reapply its
position, including failure restoration, to preserve the intended physical frame.
The first diagnostic correction exposed doubled sizing of a newly created Retina
window when sizing preceded monitor placement; the final sequence covers both
initial monitor scale and reused-window clipping. Final native diagnostics verified
2940 × 1912 for the first Retina Whole Screen result and correct frames for two
smaller selections. The last Selected Area frame was 1506 × 1430 physical pixels
with a matching 753 × 715 CSS viewport and a positive 31.8 logical-pixel image
inset. The owner still reports that boxes do not fully cover text; visual coverage
remains unresolved pending a fresh screenshot. Phase 2 is not accepted. These source checks are not exact-installer acceptance;
no installer was published and historical v0.1.0 evidence is preserved.

### OCR boundary coverage follow-up

The owner's three comparison screenshots confirmed closed outlines after the
frame correction, but exposed detector polygons/crops cutting edge glyphs in
both scan modes, notably the leading `一` and ending punctuation. The OCR adapter
now searches a bounded, glyph-sized neighborhood for cut strokes and nearby end
punctuation. It excludes large bubble/art components, unknown search-edge extents,
dark backgrounds and unrelated full characters. The original polygon remains in
the corrected convex hull; recognition uses the corrected crop. Adjusted regions
reuse `expandedCrop`, review guidance and zero uncalibrated confidence. Unchanged
regions, mask retries and short-vertical recovery retain their existing behavior.
No model/dependency or OCR response field was added.

Ten new synthetic regression cases cover horizontal/vertical text, 1×/2× image
scaling, cut leading strokes, detached end punctuation, unrelated art/characters,
unchanged geometry and corrected recognition crops. The complete local Python 3.9
run passed 87 of 88 service cases; the existing Windows checksum test requires
`hashlib.file_digest` (Python 3.11+). That exact test passed separately on Python
3.12. The pinned Python 3.11 CI run subsequently passed the complete 88-case
service suite with no skips. Frontend tests (117), TypeScript/Vite build and
service Ruff checks pass. Offline-model checks
on a clean synthetic Japanese page preserve both complete vertical sentences
and the horizontal sentence while including its previously cut edge strokes.
The updated local service is running for owner review; native visual confirmation
is pending. Phase 2 and Windows/mixed-DPI runtime gates remain open.

[Checks run 38506660742](https://github.com/chonnakanch/yomimado/actions/runs/38506660742)
passed every gate for OCR fix `17cb20a`: frontend, service, release tools and both
macOS/Windows native tests/builds. These source checks do not close Windows or
mixed-DPI interactive acceptance. The normal command-launched desktop and updated
offline service remain open; the owner's post-correction visual review is pending.

The owner subsequently confirmed full text coverage when selecting only the white
reader panel, while Whole Screen and whole-display manual selection still omitted
the leading thin stroke. These broader captures can place an entire `一` component
outside the detector box. The follow-up expands the bounded longitudinal search
to observe a complete glyph and admits nearby, aligned thin strokes as well as
small punctuation. Full neighboring characters, bubble/art components, distant
components and truncated search-edge components remain excluded. Five additional
regression cases cover disconnected strokes at 1×/2× in both orientations and
recognition when the entire leading stroke was omitted. Broader native visual
confirmation is pending; the white-panel confirmation remains recorded.

[Checks run 38507911101](https://github.com/chonnakanch/yomimado/actions/runs/38507911101)
passed all gates for disconnected-stroke fix `05adc1d`, including the complete
93-case service suite, 117 frontend tests and both native tests/builds. An
offline-model probe with a synthetic crop deliberately omitting the entire
leading stroke changed recognition from `緒に日本語を勉強しましょう。` to
`一緒に日本語を勉強しましょう。`; the corrected crop and polygon include that
stroke. The updated local service remains running with the normal development
app. On 2026-10-14 the owner confirmed that Whole Screen now fully covers the
leading `一`, following the earlier successful white-reader-panel selection.
Post-fix confirmation of whole-display manual selection is not separately recorded.
Phase 2 owner approval and Windows/mixed-DPI interactive acceptance remain open;
no popup phase, installer acceptance or publication is implied.

### Toolbar feedback and compact-layout refinement

The owner requested these Phase 2 refinements before the popup phase: remove the
automatic status text row, indicate overlay state by icon, highlight the current
scan mode, put scan progress in its button, and keep compact controls on one row.
The toolbar now reads native active/retained scan mode, presents an indeterminate
spinner with phase text inside that button and retains exact-session cancellation
there. Visibility uses the eye icon and accessible pressed state. Routine messages
remain screen-reader announcements; warnings expose error/model-setup details only
on explicit activation, with Escape/focus return.

Compact mode retains Selected Area and Whole Screen as accessible icon buttons,
Rescan, visibility/status and expand beside the drag handle. Scoped border-box
controls, a non-wrapping row and sufficient native content width prevent the old
expand-arrow wrap. Narrow work areas also use the compact form. No capture, OCR,
dictionary, translation, persistence or popup content behavior was changed.

WebKit inspection of the actual React/CSS with mocked native IPC verified
520 × 56 expanded and 224 × 48 compact dimensions: controls remained on one row
and inside the frame. Mode selection, button-contained progress, hidden-state
icons and requested error details were visually checked. This browser check is
not native window/input acceptance. The temporary review fixture was removed
from ignored build output. Final source checks passed 122 frontend tests,
TypeScript/production Vite build, desktop/document formatting, 50 native tests,
Cargo formatting and the macOS debug build. The normal command-based development
app was relaunched with the updated native mode contract. On 2026-10-14 the owner
confirmed that Whole Screen highlighting, progress inside the scan button,
icon-only visibility status and compact controls on one row match the request.
Windows/mixed-DPI interactive acceptance remains open. Phase 3 remains unstarted.

[Checks run 38512106734](https://github.com/chonnakanch/yomimado/actions/runs/38512106734)
passed all gates for toolbar refinement `74cf470`, including frontend, service,
release-tool checks and macOS/Windows native tests and builds.

## UI redesign — Phase 3 Compact popup review

On 2026-10-14, after confirming the toolbar refinements, the owner authorized
continuation to the selected **Compact popup** design. Phase 3 is implemented
for source/result review; saved-collection and settings redesigns remain unstarted.

- [x] Sentence-first source with explicit Copy/Save, close, analysis status/retry
      and no automatic word, kanji or translation lookup.
- [x] Continuous Japanese token controls preserve Unicode gaps, punctuation and
      newlines. Selected vocabulary uses 30 px surface, 16 px hiragana presentation,
      base form, token POS, numbered senses and match warnings.
- [x] Collapsed alternative matches retain ranked order and entry-specific raw
      readings/senses when saved. Missing/error states retain Save without meaning.
- [x] Dedicated kanji controls, labeled on’yomi/kun’yomi and local attribution;
      compounds load only on expansion and retain independent retry/cache state.
- [x] Hidden OCR correction draft with Apply and analyze / Cancel, editor focus
      return and stale lookup/translation/copy/save invalidation on commit.
- [x] Explicit local translation and matching sentence-save output, copy success/
      failure and save retry. Existing clients, storage formats and providers retained.
- [x] Native preferred width 420 logical px, work-area height cap 70%, target-scale
      positioning and rejection of previous-popup resize queries. Sentence/actions
      stay above bounded scrolling details; long sentences scroll independently.
- [x] Owner confirmed the normal macOS development popup looks right, stays within
      the screen and returns keyboard focus correctly after word/kanji/compound
      exploration and Edit OCR text → Cancel / Escape on 2026-10-14.
- [ ] Windows and mixed-DPI interactive acceptance. Installer/publication work is
      not authorized by this source change.

Local checks passed 132 frontend tests in 19 files, TypeScript/production Vite
build, Prettier, 51 native tests, Cargo formatting and the macOS debug build.
WebKit inspection of actual React/CSS with the real local service verified the
420 px view, a 280 × 320 narrow view, long-sentence scrolling, no horizontal
overflow, sentence/details separation, kanji/compound lookup and explicit copy
feedback. This browser frame does not certify native placement or input routing.
The temporary review fixture is removed from ignored build output before handoff.
Opaque popup text colors have contrast ≥5.32:1 on their used surfaces; selected
token text is 7.05:1 and focus on the popup surface is 6.29:1. Native font fallbacks
remain offline. No service, dependency, font, model, release version or installer
change was made. The normal command-based development app was relaunched for review.

[Checks run 38536586847](https://github.com/chonnakanch/yomimado/actions/runs/38536586847)
passed all gates for Phase 3 source `d90aaa4`, including frontend, service,
release tools and macOS/Windows native tests and builds. The owner accepted the
popup in the running macOS development app. Clipboard success was verified in
WebKit, not separately in both native hosts. Windows/mixed-DPI runtime acceptance
remains open; Phase 4 is unstarted pending further authorization.

### Phase 4 navigation refinement — grouped Saved menu

On 2026-10-14 the owner requested one menu for saved words and sentences. The
toolbar now has **Saved**, opening the existing secondary window directly to a
shared library with **Words** and **Sentences** tabs. The legacy main window also
uses one Saved control; existing words/sentences query routes remain compatible.
Tabs support Left/Right, Home/End, selected semantics and roving focus. Opening
or returning to a collection refreshes it; independent request guards prevent
older list responses from overwriting a newer refresh.

The existing records, list/delete APIs, stored order, attribution, translation,
dates, loading/error/empty states and confirmed removal are retained. The focused
library route shows collections directly. Full collection-row and settings polish
remain planned work, separate from this requested navigation change.

Checks passed 136 frontend tests in 19 files, TypeScript/production Vite build,
Prettier, 51 native tests, Cargo formatting and the macOS debug build. Native
Windows/mixed-DPI interactive acceptance remains open. No saved-data migration,
service/dependency/release change or installer publication is included.

Browser inspection of the actual app at 700 × 480 verified one Saved heading,
Words/Sentences tab selection, keyboard focus, real saved-word data, sentence
loading/empty states and no horizontal overflow. The normal command-based app
is running with the new native Saved route. Browser evidence does not replace
Windows/native menu acceptance.

[Checks run 38541259393](https://github.com/chonnakanch/yomimado/actions/runs/38541259393)
passed all gates for grouped Saved source `bacab2d`: frontend, service,
release tools and macOS/Windows native tests and builds.

### Phase 4 Saved library layout — implemented for review

The owner authorized continuation after the grouped Saved navigation. Saved words
and sentences are now separate feature-owned views inside the shared Saved menu.
Word rows retain stored surface, reading, base form, numbered meanings and visible
JMdict attribution; source/context and local saved date use a collapsed disclosure.
Sentence rows keep the full Japanese and any stored English output, with a saved-date
disclosure and explicit Japanese-only state. Long text wraps at narrow widths.

The views share a small typed list/delete lifecycle while retaining existing clients
and schemas. Loading/error/empty/removal states are independent for each collection.
Earlier lists cannot overwrite newer loads or reintroduce a removed item; confirmed
removal locks duplicate actions and restores keyboard focus to a nearby row/Refresh
without stealing focus from another tab. Failures retain data and permit retry.
Closing/reopening or returning to a tab refreshes the selected collection.

Local verification passed 142 frontend tests in 19 files, TypeScript/production
Vite build, Prettier and diff checks. Added cases cover stored ordering, old record
fields, collapsed details, date fallback, existing translations, removal confirmation,
duplicate removal, stale-list rejection, retry and focus restoration. Native and
service source/API/storage formats are unchanged.

[Checks run 38545692404](https://github.com/chonnakanch/yomimado/actions/runs/38545692404)
passed all gates for Phase 4 source `aed09f4`: frontend, service, release tools,
and macOS/Windows native tests and builds. These source checks do not replace
the owner or Windows/mixed-DPI interactive acceptance below.

Browser inspection of actual components with synthetic saved records and mocked
native IPC verified 700 × 480 and 280 px layouts, long Japanese/readings, disclosures,
sentence translations and no horizontal overflow. Japanese word/source text remains
20 px; no remote font is introduced. This is browser evidence, not native Windows
acceptance. The temporary fixture is removed from ignored build output before handoff.
The normal development app is available for owner review.

- [x] Owner acceptance of the Phase 4 library layout and interactions on 2026-10-14.
- [ ] Windows/mixed-DPI interactive acceptance.
- [x] Owner authorized continuation to Phase 5 Settings. No installer/publication
      or version change is authorized by this source work.

### Phase 5 Settings — approved by the owner

On 2026-10-15 the owner approved Phase 5 after the Settings implementation and
subsequent toolbar, capture, popup and debug refinements. The latest application
source is `9726dc1`; approval was given with documentation at `96b9356`. This
accepts the phase's implementation and design. It does not substitute for
unrecorded native checks or authorize a new phase, version change or installer
publication.

On 2026-10-14 the owner accepted Phase 4 and authorized the Settings phase.
At the owner's request, Saved, Settings and Sources & licenses now use independent
native windows with no shared Saved/Settings navigation. Settings uses
keyboard-accessible Scan & OCR and Reading categories. The
Settings route opens Scan & OCR; Sources opens attribution in its own window; the native
secondary-view contract also supports Reading directly. Saved and legacy
words/sentences query routes remain compatible.

Scan & OCR retains native model status, checksum-verified import/replacement,
cancel/error handling and restart guidance. Refresh rejects older status responses;
imports cannot overlap in the view. Development service setup is labeled separately
from packaged installation without claiming service readiness. Capture permission
and shortcut guidance describe actual modes; automatic page cropping is removed
from the secondary user flow, while its tested native helpers remain. Reading keeps
the existing local-storage key and off-by-default estimated-order preference, with
explicit save errors. About retains existing links and full packaged notice guidance.

The existing native close-to-hide, open/unminimize/focus and explicit Quit paths are
preserved. At the owner's request, the native title bar and window buttons are
restored after confirming the external quit-on-close utility caused application
exit. Temporary app-owned controls, their command and tests are removed. Native
close hides only its secondary window without ending the other windows or
toolbar/service/reading session. All secondary windows are hidden before capture
and included in the existing visibility restoration path. Window permissions are
extended to the two new labels. No OCR/geometry/dictionary/translation/storage/
dependency/version or installer behavior was changed. Native Windows/mixed-DPI runtime acceptance remains
open, including current Settings lifecycle; automated native builds do not certify it.

Window-separation verification passed 148 frontend tests in 20 files, TypeScript/production
Vite build, full desktop Prettier, 52 native tests, Cargo formatting and macOS debug
build/startup. Behavior coverage includes category routes and keyboard navigation,
reading preference persistence/failure/retry, status retry/old-response rejection,
model cancellation/replacement failure/retry and duplicate import prevention.
Before separating the windows, actual components with mocked packaged status were inspected in WebKit at 700 × 480
and 280 px width. All three categories wrap without horizontal overflow; attribution
and permission/shortcut guidance remained accessible. The temporary fixture was removed
from ignored build output. These browser checks do not certify native file pickers,
model replacement or permission changes. Current regression checks verify isolated
Saved/Sources rendering, Settings category navigation, distinct menu destinations,
collection aliases, and inclusion of each destination in native close/capture policy.
The normal command-based app is open for review; simultaneous-window and native
close/reopen acceptance of this separation remains pending.

The owner also requested removal of the shared instructional footer and the
**Focus regions** overflow item. More actions now contains Saved, Settings,
Sources & licenses and Quit. Native region focus/navigation handling is retained;
help text no longer directs users to the removed menu action. The menu follow-up
passes 17 toolbar/overlay tests, TypeScript/production build and desktop Prettier.

- [x] Owner approval of Phase 5 implementation and layout on 2026-10-15.
- [ ] Explicit native-button close/reopen and simultaneous-window verification
      after restoring native controls; earlier external-utility findings are retained.
- [ ] Windows/mixed-DPI interactive acceptance, including Quit/service cleanup.
- [ ] Future installer/release work requires separate owner authorization.

[Checks run 38567439854](https://github.com/chonnakanch/yomimado/actions/runs/38567439854)
passed all gates for Settings source `2a66ba4`, including frontend, service,
release tools and macOS/Windows native tests and builds.

The owner confirmed the Settings categories work, but reported that the macOS red
close button also removes the toolbar and OCR boxes. A normal detached development
launch reproduced process exit after the main close/hide callback without an
ExitRequested event. A temporary native close/reopen/explicit-Quit smoke exercise
passed, showing that programmatic close alone did not cover the native button path.
The follow-up change vetoes main-window closure immediately and queues hiding from
a worker so the native close callback returns before the hide is processed. Local
native tests (51) and formatting pass. Cross-platform
[Checks run 38570389158](https://github.com/chonnakanch/yomimado/actions/runs/38570389158)
also passed for `10b8c58`, but the owner's native red-button retest still exits the
app. This follow-up does not resolve the reported issue; Phase 5 acceptance remains
open. A debugger trace records `NSApplication terminate:` reached through the
native `_handleAEQuit` Apple-event handler after the main close/hide completes.
The sender attribute was unavailable at that deferred termination breakpoint.
The original close handler is restored because deferral does not fix the reported
behavior. Temporary lifecycle diagnostics and smoke code are removed from source.
The owner's own Terminal launch also exits, as does the app-owned Close action.

Local inspection subsequently found Vorssaint 3.4.1's **Quit on close** enabled,
with only Finder and Phone excepted. Its published implementation explicitly quits
apps that hide their final user window and matches exceptions by bundle identity.
The owner authorized adding a YomiMado exception. The `com.yomimado.desktop`
exception was saved and verified in Vorssaint's UI, retaining the global setting
and existing exceptions. However, macOS reports no bundle identifier for the bare
command-launched development process, so this exception cannot protect that process.
Adding an embedded development plist did not change the reported identity and was
removed. The owner subsequently closed Vorssaint and confirmed that closing Saved
keeps YomiMado running, identifying the external utility as the cause. The owner
chose to retain the YomiMado exception and restore native window controls. No global
toggle or Quit interception was applied. The temporary custom-control source
(`243f97e`, verified with 151 frontend and 51 native tests) is removed; the existing
native hide-on-close handler is retained. Final native-button acceptance after this
restoration and Windows/mixed-DPI interactive acceptance remain open.

### Toolbar work-area placement and consistent control sizes — accepted on macOS

The owner reported that opening More actions at the bottom of the screen moved
the toolbar, and compact/expanded controls changed size. Native placement now
anchors the visible row separately from the transparent window frame. Panels grow
below when there is room or above otherwise; close restores the original row
position. On short work areas, panel height is bounded and the panel scrolls.
The previous row offset is retained across native resizing, including fractional
display scaling and negative monitor origins. Resize requests are serialized;
late responses after menu dismissal cannot restore stale UI placement.

Both forms keep a 56 logical px row and 36 px controls. Expanded width is 536 px;
compact width is 244 px, retaining both scan icons, Rescan, visibility and Expand
on one row. Dragging or keyboard movement dismisses panels. Menu/status focus is
applied after placement, preserving keyboard navigation and Escape focus return.

Verification passes 149 frontend tests, 55 native tests, production frontend and
macOS native builds, desktop Prettier and Cargo formatting. Native geometry
regressions cover top/bottom opening and closing at 100%, 125%, 150% and 200% scale,
negative work-area origins, short work areas and expansion near the right edge.
WebKit inspection of actual components with mocked native placement at 600 × 480
confirmed the row stayed at y=404 before, during and after menu opening; both forms
were 56 px tall and all controls 36 px tall. A 600 × 220 inspection confirmed a
bounded scrolling menu and keyboard access to the last action. The temporary
ignored fixture is removed. These browser checks simulate native frame placement;
Windows/mixed-DPI interactive acceptance remains pending.

On 2026-10-14 the owner tested the normal macOS development app at source
`cffe385` and confirmed both fixes: More actions opens above near the bottom
without moving the toolbar row, and collapse/expand keeps control sizes consistent.
This accepts the toolbar refinement on the tested macOS setup; it does not certify
other monitors/scales, Windows or a packaged installer.

### Dropdown transient flicker — separate native popover

The owner's subsequent recording revealed a one-frame toolbar jump when the menu
closed, despite correct settled positions. A local timing/atomic-frame experiment
still flickered in the owner's retest and was removed without committing it.
More actions now renders in its own reusable, transparent native window, anchored
to the toolbar's measured row. Opening or closing the menu never changes toolbar
bounds. Placement retains above/below selection, physical/logical scaling, work-area
limits and scrolling. The popover loads hidden and is revealed after measurement.

Keyboard arrows/Home/End, Escape focus return, outside-focus dismissal, four menu
destinations and Quit are retained. Generation checks prevent a closed or replaced
menu's delayed measurement from revealing it again. Capture dismisses/hides the
popover before taking a screenshot, and does not restore it afterward. Only this
app window is added to existing window capabilities; no dependency or OS preference
is changed. Status details remain in their existing inline panel.

Verification passes 152 frontend tests in 21 files, 57 native tests, production
frontend and macOS native builds, desktop Prettier and Cargo formatting. Regression
coverage verifies no toolbar resize on menu open/dismiss, keyboard/destination
behavior, delayed-request invalidation, and popover alignment at 100%, 125%, 150%
and 200% scale. On 2026-10-14 the owner confirmed the flicker is gone in the normal
macOS development app, and reported an unwanted focus ring on mouse opening.
The popover now tracks its own keyboard/pointer input, preserving initial focus
and arrow/Home/End navigation while showing the blue inset ring only during
keyboard navigation. The owner then tested source `8d659c4` in the normal macOS
development app and confirmed clean mouse opening, the inset keyboard ring,
Escape dismissal and outside-click dismissal all work correctly. This accepts
the flicker/focus refinement on the tested macOS setup. Windows/mixed-DPI
interactive acceptance remains pending; no packaged installer was tested.

WebKit inspection of the actual React components with native windows simulated
confirmed mouse opening has no outline, ArrowDown focuses Settings with a 2 px
inset ring, and Escape returns focus to More actions. The simulated toolbar row
remained at y=404 throughout. Temporary ignored preview fixtures were removed.

### Keyboard reading replaces the legacy reading controls

On 2026-10-15 the owner reported that arrow navigation no longer worked. Removing
Focus regions had also removed the explicit entry that focused the native overlay;
the SVG arrow handlers remained, but normal scan completion deliberately leaves
keyboard focus in the reader. The owner approved **More actions → Read with
keyboard** as the replacement for the first-release Reading-order controls.

The new action uses the existing guarded native focus command and is disabled
without visible completed OCR results or during a scan. Arrows/Home/End select
regions; Enter/Space opens the selected popup. Keyboard popup dismissal returns
to the originating region. Escape from region navigation hides overlays and
focuses the toolbar. An HTML focus target handles navigation if a webview cannot
focus SVG polygons. Scan completion and hover still do not steal keyboard focus.
The old preference, Previous/Next text panel, styling and storage listener are
removed. Existing preference data is left untouched and ignored. Reading settings
now explains keyboard reading. Estimated scan ordering and OCR geometry are
preserved; this does not infer manga panel order or change published installers.

Verification passes 154 frontend tests in 20 files, 57 native tests, the production
frontend build, macOS native build and desktop formatting. Regression checks cover
the menu's visible-result guard, explicit native focus entry, HTML fallback arrows,
activation and region focus return. WebKit inspection of the actual components
with mocked native commands confirmed explicit entry, a blue selection moving
between vertical regions, and Enter activating the selected region. Changing
selection did not issue OCR, tokenization, dictionary or translation commands.
The temporary ignored synthetic fixture was removed. On 2026-10-15 the owner
tested source `4ab2234` in the normal macOS development app and confirmed that
Read with keyboard enters region navigation, arrows move the blue selection,
Enter opens its popup, and Escape returns to the region so navigation continues.
This accepts the replacement on the tested macOS setup. Windows/mixed-DPI
interaction and packaged-installer acceptance remain unverified.

### Whole Screen restores automatic manga-page cropping

On 2026-10-15 the owner reported browser/menu-bar text becoming OCR regions and
requested the earlier smart manga-page capture behavior. The redesign had kept
the detector but intentionally bypassed it in Whole Screen. The owner's current
request supersedes that original literal-full-monitor OCR requirement.

Whole Screen still acquires the complete target monitor locally, then uses the
existing conservative page detector before OCR. A confident page/spread is cropped
with its physical/logical offsets preserved and recorded as the successful scan
area. An uncertain boundary uses a valid saved manga area for the same display
layout, or opens the selector to draw/save one. It never sends the entire monitor
to OCR merely because detection failed. Selected Area continues to scan the exact
manual rectangle; Rescan takes fresh pixels from the last successful crop/area.
Tooltips, Scan & OCR help, usage and the redesign documents describe this behavior.
The legacy automatic entry shares the same crop/session-update helper.

Verification passes 158 frontend tests in 20 files, 59 native tests, production
frontend and macOS native builds, desktop Prettier and Cargo formatting. Coverage
includes cropped OCR input/overlay metadata, saved/missing/invalid-area fallback,
drawing a replacement area, two-page spread detection below browser/menu text,
and crop offsets on negative-origin displays at 100%, 125%, 150% and 200% scale.
A temporary local diagnostic against the owner's attached 2930 × 1912 screenshot
found the spread at x=217, y=194, width=2507, height=1718, excluding the top browser
controls. The diagnostic was removed; the attachment is not a repository fixture.
The production detector algorithm is unchanged. Native macOS owner acceptance and
Windows/mixed-DPI interaction remain pending for the restored entry path.

### Manga-area fallback guidance refinement

The owner reported the initial automatic-detection fallback still showed the
legacy warning design. The native log subsequently recorded successful automatic
crops for a spread (2504 × 1728) and a single page (1138 × 1521), but this does not
establish why the first scan was uncertain or certify visible coverage. On 2026-10-15
the owner confirmed that only the first scan failed; later scans detected pages
automatically. The initial failure's cause and recurrence after a fresh launch
remain unverified. The conservative detector was not changed based on this single
fallback, and no additional owner test was requested.

The fallback now uses a token-based **Select manga pages** card with page/spread
drawing guidance, saved-area explanation and Cancel/Esc. Expected uncertain bounds
use a polite status rather than an error warning. Actual capture/save errors remain
alerts. The card hides while dragging; its pointer events cannot start a capture
selection. Both legacy automatic and Whole Screen fallback share this presentation.

Verification passes 159 frontend tests, the production frontend build and desktop
formatting. The existing unchanged native source passed 59 tests and its macOS build
in the preceding restoration. WebKit inspection of the actual capture component
with native commands mocked confirmed the card layout and that Cancel issues only
cancellation, without selecting or invoking OCR. The private synthetic fixture was
removed. Native fallback appearance, the first detection failure, and Windows/mixed-DPI
interaction remain open for owner review.

### Approved Edge hint replaces the selection card

On 2026-10-15 the owner reported that the fallback card obscured the starting area
for a manga selection and approved the Edge hint proposal. Manual selection and
the fallback/configure flow now use a bottom-centred, approximately 30 logical px
pill: **Drag around pages · Esc cancel** (or **Drag to capture · Esc cancel** for
Selected Area).
It ignores pointer events, so selection can start through its text. Pointer-down
hides it immediately. Escape retains the existing native
cancel path; pointer cancellation clears the unfinished rectangle and restores
the hint. The former heading, explanatory paragraphs and Cancel button are removed.
Actual capture/save failures retain their accessible alert above the hint.

Verification passes 160 frontend tests, production frontend build and desktop
formatting. Normal macOS development startup succeeds with unchanged native source.
WebKit inspection of the actual component with native commands simulated measured
206 × 30 px at both 1280 × 720 and 320 × 480 viewports. A drag starting on the hint
reached the selector and hid the hint; a tiny drag made no capture/OCR call, and
Escape issued the session-bound cancellation command. The temporary private fixture
was removed and viewport reset.

On 2026-10-15 the owner tested source `184bdf1` in the normal macOS development app
and confirmed that starting a Selected Area drag over the bottom hint and pressing
Escape keeps the hint out of the way and the page clear. This records native
acceptance of the Edge hint on the tested macOS setup. Windows/mixed-DPI interaction
remains pending. Manga-page detection and its first-scan observation are unchanged
by this presentation refinement.

### Compact OCR review status in the learning popup

On 2026-10-15 the owner requested a minimal icon and short label in place of the
large approximate-region warning above the Japanese sentence. Review/approximate
regions now show a 16 px outlined status icon and **Check OCR** beside the Japanese
heading. The full reason and correction guidance remain in the hover tooltip and
screen-reader text. The dashed warning block and its duplicate Edit OCR text link
are removed; the existing secondary correction action and OCR review metadata are
preserved. No capture, detection, translation or native-window behavior changes.

Verification passes all 18 popup tests, TypeScript and the production frontend
build, plus desktop formatting. WebKit inspection of the actual React component
with synthetic text and native/service calls simulated confirms the indicator fits
on the heading row at 420 px and 280 px widths without overlap or horizontal
overflow. Edit OCR text opens its editor; Cancel restores focus to that action.
The temporary fixture was removed and viewport reset. Normal macOS development
startup succeeds. Windows/mixed-DPI visual acceptance remains unverified.

The owner subsequently requested a smaller warning indicator. **Check OCR** now
uses the 11 px caption token with a 12 px icon and 2 px internal gap, down from
12 px text and a 16 px icon. Its gap from Japanese is reduced from 12 px to 8 px.
The tooltip, screen-reader detail and correction action are unchanged. Verification
passes the 18 popup tests, production frontend build and desktop formatting.

### More orange OCR region outlines

On 2026-10-15 the owner requested more orange detected-region boxes. The dedicated
region tokens now use saturated orange `#E8750B`, brighter orange `#F58A1F` on
hover, and a matching 8% hover fill. Blue selection/keyboard focus, dashed review
states, polygon geometry and stroke widths are unchanged. Other accent controls
retain their existing palette. Overlay tests, the production frontend build and
desktop formatting pass; native Windows/mixed-DPI visual acceptance remains open.

The owner's screenshot showed that the 1 px lines remained hard to distinguish.
The follow-up uses vivid orange `#F56B00` with a 2 CSS px default stroke, up from
1 px; hover uses `#FF7900` at 3 px. Blue selection/focus also uses 3 px. Review
dashes, transparent default fill, polygon coordinates and non-scaling strokes are
preserved. The default orange measures approximately 3.01:1 against white; contrast
against manga artwork varies. Five overlay tests, the production frontend build
and desktop formatting pass. WebKit inspection of the actual region component
with synthetic Japanese text confirms the orange 2 px stroke, retained review
dashes and blue 3 px selection. The private fixture was removed. Native visual
acceptance of this thicker treatment remains open on macOS and Windows/mixed-DPI.

### First Whole Screen recognition stalls in a never-shown webview

On 2026-10-15 the owner reported that Whole Screen remained at Recognizing on a
fresh app launch until Selected Area was used. Their log confirms capture and
automatic manga cropping completed. This is distinct from the earlier uncertain
page-detection fallback. The owner launched the development app independently;
their process and OCR service were left running during this investigation.

Whole Screen/Rescan create a hidden capture webview, whereas Selected Area shows
it before capture. The selector builder now disables background throttling using
the existing Tauri API, supported on the project's macOS 14+ target. This keeps
the hidden webview's IPC/network continuations runnable without showing a selector
or taking focus. Windows ignores this macOS policy; its runtime gate remains open.

A separate native WebKit probe used the actual CaptureSelector/requestOcr flow,
a synthetic PNG (3,081,260 base64 bytes) and an isolated loopback OCR stub. Immediate
replies completed under both policies. With a 12-second reply delay, the default
hidden policy stalled after Requesting despite the stub returning HTTP 200 and
reached the probe's 30-second failure bound. A fresh process with throttling disabled
processed the same delayed response and reached overlay publication. No user screen
was captured and the real OCR service was not restarted. The private probe source,
HTML and configuration were removed; its isolated stub was stopped.

OCR requests now have a three-minute deadline covering image loading, upload and
response-body parsing. Timeout aborts the browser request, reports failure through
the existing session-bound finish path and cannot publish a late result. Aborting
the client request does not promise to stop inference already running in Python.
Metadata-only native OCR-stage logs distinguish request, recognized response and
publication without recording screenshots or Japanese text.

Verification passes 165 frontend tests, including first Whole Screen under
StrictMode/suspended animation frames, upload/body timeout and late-response guards,
plus 59 native tests, TypeScript/production frontend build, desktop formatting,
Cargo formatting and the macOS native build. On 2026-10-15 the owner confirmed
that source `9edd2c2` fixed the reported first-launch Whole Screen stall on their
real reader. This records acceptance of that fix on the tested macOS setup;
Windows/mixed-DPI runtime acceptance remains open. The native policy requires
restarting the command-launched app; no automatic restart or installer/version
change was performed.

On 2026-10-15 the owner additionally confirmed that full-screen capture OCR works
in their current macOS development setup. This records owner acceptance of the
Whole Screen capture-to-OCR flow. The report does not establish separate results
for every page-detection fallback, multi-monitor configuration or Windows/DPI
case, and does not apply to a packaged installer.

### Debug-only hover tooltips and redesigned capture preview

On 2026-10-15 the owner requested that hover tooltips appear only in the existing
capture debug mode, and that its preview match the approved redesign. One shared
flag reader now controls `VITE_CAPTURE_DEBUG=1` across capture, toolbar, OCR polygons
and the learning popup. Normal mode omits hover title attributes/SVG titles while
retaining accessible names, scan descriptions, OCR review metadata, dashed regions
and Check OCR. Debug mode preserves the detailed tooltips and existing explicit
Show overlay review step. No production Settings toggle is added.

The capture preview now uses shared tokens, compact utility buttons, readable
Japanese rows, a labeled geometry legend and feature-owned CSS. Final/review
polygons share the current orange and dash cues; candidates use a dedicated cyan
token and filtered boxes use muted dots. Geometry and detector details are collapsed
initially, with all existing coordinates, retries, reasons and crops retained.
The exact in-memory capture keeps its aspect ratio. Narrow layouts stack the
image and results in independent keyboard-focusable scroll panes. Loading and
errors retain the image; Show overlay waits for a response and Close stays usable.

Verification passes 170 frontend tests, TypeScript, normal/debug production
frontend builds and desktop formatting. Tests cover both tooltip modes with
accessible labels preserved, explicit debug publication, diagnostics and errors.
WebKit inspection of the actual preview with synthetic capture/response data at
1280 × 720 and 320 × 480 confirms no horizontal clipping, image fitting, keyboard
disclosures, loading/error presentation and action callbacks. The temporary fixture
and isolated preview server were removed/stopped and viewport reset. The owner's
app and OCR service were not restarted during that implementation review;
native/service code and release artifacts are unchanged.

After stopping their own app, the owner authorized a normal command-based launch
and native verification of source `9726dc1` with capture debug enabled. The existing
local service reported the manga engine ready. A separate Helium tab displayed the
repository's synthetic Japanese reader. Native logs confirm capture, recognized
OCR and a held debug preview; the owner confirmed that the preview appeared.
The owner then confirmed that Geometry and Detector stage expand, Show overlay
displays the OCR boxes, and hovering an OCR region and Whole Screen shows the
debug tooltips. The native log independently confirms `OCR overlay displayed
(manga)`. This records macOS acceptance of those debug interactions. Native UI
automation could not target the unbundled process, so the owner performed its
clicks while the agent inspected logs. Automatic page detection was uncertain on
this fixture and reused the saved-area fallback; this check does not certify
automatic crop coverage. The debug app was left running. Normal-mode hover
suppression retains automated coverage; Windows/mixed-DPI native review remains
open.

### Complete checks and redesign code review

On 2026-10-15 the owner requested complete frontend, native and OCR-service checks
and a code-quality review. The [review record](ui-redesign-review.md) describes
scope, findings and remaining native acceptance boundaries. Review found a menu
destination failure could be rendered in an already-hidden popover; errors now
reach the toolbar's existing status control through a targeted event. Regression
tests cover both ends. An unnecessary native return was removed, and two existing
IPC commands retain documented, narrowly expected argument-count lints.

Local verification passes 172 frontend tests, normal/debug production builds and
Prettier; 59 native tests, locked macOS build, Cargo formatting and strict Clippy;
93 OCR-service tests with zero skips, Ruff/format and dependency consistency; and
229 release-tool tests with script Ruff/format checks. Full service verification
used the project's Python 3.11.17 runtime after an initial Python 3.9 environment
failed the Windows-only graph verifier's Python 3.11 API call. Rust is 1.98.1.
No service, model, dependency, version or installer change was made. Windows and
other unrecorded native interactions remain separate acceptance gates.

The owner subsequently requested removing the two Clippy exceptions and selected
automated coverage plus a prepared checklist for Windows. Both exceptions are now
removed: controls obtain their app handle from the existing window, and popup mode
comes from native OCR state. CI runs strict all-target Clippy on macOS and Windows.
The unchanged stale-frame guard now has direct regression coverage for every pair
of 100/125/150/200% scales and shifted/clipped frames on negative origins, bringing
the local native suite to 60 tests. The
[Windows redesign checklist](ui-redesign-windows-checklist.md) separates source UI,
mixed-DPI, input/focus, independent-window and recovery cases from future installer
checks. No interactive hardware result is inferred or marked passed.

The new strict Windows gate exposed unused macOS pointer-routing state and
release-only Windows service startup code in debug targets. Platform/build
conditions now match their consumers without suppressing warnings. Packaged
service behavior is unchanged, and its Windows SDK/job/readiness tests remain
enabled in the native test target.

### Follow-up quality fixes: OCR admission and Windows smoke navigation

The owner approved fixes for three follow-up review findings. Recognition now
admits one worker at a time, covering lazy model initialization and inference.
Overlapping requests receive HTTP 503 with a retry hint instead of sharing model
state or queuing screenshots. The worker retains admission after client
cancellation until inference actually finishes. Four new regression cases bring
the service suite to 97 passing tests with zero skips; all 229 release-tool tests
also pass locally, along with service/script Ruff and formatting checks.

Windows installed checks now follow the redesigned toolbar → More actions →
Settings flow, verify secondary-window close keeps the toolbar alive, and use
explicit Quit before service/port cleanup assertions. A shared Windows PowerShell
5.1 driver and synthetic two-process UI test in Checks CI cover window discovery,
button/menu-item invocation, close/reopen, process isolation and Quit. The release
workflow invokes the driver under the required Framework PowerShell runtime.
Actual installed-app and physical mixed-DPI results remain unrecorded; no installer
or release workflow was run. Future macOS packaging must refresh/review the frozen
OCR runtime seed for the changed service source; its mismatch rejection remains.

On 2026-10-16, source commit `e0ebe97` passed all jobs and the aggregate gate in
[Checks run 38836706682](https://github.com/chonnakanch/yomimado/actions/runs/38836706682),
including the real Windows UI Automation driver against the synthetic WPF fixture.
Frontend/service/release-tool checks, strict Clippy, native tests and debug builds
passed on both supported native CI platforms.

### Toolbar launch placement

On 2026-10-16 the owner requested bottom-screen startup instead of the fixed
top-left coordinates. The toolbar now starts centered near the bottom of the
primary display's usable work area, with the existing 12 logical px inset above
system UI. Native setup positions it before showing it; the first frontend
measurement accounts for the saved compact preference, then normal drag/resize
anchoring resumes. A geometry regression covers both widths, 100/125/150/200%
scales, offset/negative work areas and a constrained work area.
Local verification passes 61 native tests, strict all-target Clippy, Cargo
formatting and the locked macOS debug build; 25 toolbar/menu frontend tests,
TypeScript/Vite production build and changed-file Prettier checks also pass.
Physical Windows placement remains part of the prepared acceptance checklist.

### Redesign implementation closed — 2026-10-16

The owner requested closure after the bottom-screen toolbar change. The source
implementation is complete through `cd2d202`, with all jobs and the aggregate
gate passing in
[Checks run 38837880179](https://github.com/chonnakanch/yomimado/actions/runs/38837880179).
No additional redesign phase is active.

Future release preparation retains the final macOS smoke test, the prepared
Windows/mixed-DPI checklist, recorded dependency-advisory triage, a reviewed
macOS frozen-runtime refresh for the changed OCR service, version/release notes,
protected-main integration and exact-installer acceptance before owner-approved
publication. Untested cases remain unrecorded. No installer, tag or public release
was created by this closure; historical v0.1.0 evidence is unchanged.

### Version 0.2.0 release preparation

On 2026-10-16 the owner requested the `0.2.0` version bump, protected-main merge
and release build. The five version files agree, with no dependency changes.
Release notes describe the redesign. Version-updater tests now choose a distinct
target dynamically, retaining write-failure/rollback coverage when the repository
itself reaches `0.2.0`.

The current macOS runtime seed is for `42edd4e`; reuse correctly rejects the
redesigned source and changed frozen OCR modules. Prepare and verify a refreshed
runtime/source seed before activating new pins. Keep source/licence review and
exact-installer publication approvals distinct. No new human approval or installed
acceptance is inferred from the build request.

The owner approved the refreshed source/licence delivery only on 2026-10-16,
as `chonnakanch`, after reviewing the 477 entries/75 archives and retained limits.
The replacement private seed uses `fae4d28`; all dependency/native inventories
and 74 dependency archives match the reviewed baseline. Both private and
approved-source macOS builds pass exact mounted/frozen/offline verification.
PR [#7](https://github.com/chonnakanch/yomimado/pull/7) is drafted; required source
[Checks 38839347283](https://github.com/chonnakanch/yomimado/actions/runs/38839347283)
pass. All three private seed uploads now independently match the local SHA-256
values in GitHub. Replacement source/hash pins are activated; the runtime-reuse
rejection remains intact. Required Checks and the protected-main merge precede
the hosted release build. No installed-app or publication approval is claimed.

Protected PR #7 subsequently merged at
`645ba088118f41880abfc37df1b595fa85e3ad42` after
[Checks 38840926023](https://github.com/chonnakanch/yomimado/actions/runs/38840926023)
passed on the final seed pins. The merged tree is identical to the tested head.
Main [Checks 38841491986](https://github.com/chonnakanch/yomimado/actions/runs/38841491986)
and [Release 38841492110](https://github.com/chonnakanch/yomimado/actions/runs/38841492110)
started automatically. All main Checks jobs and the aggregate gate pass. Release
planning and all private input hashes pass; the macOS installer job passes in
10 minutes 50 seconds. Windows produced a setup but failed installed startup
because the driver assumed Invoke on the ExpandCollapse toolbar menu button.
Later Windows gates, combined verification and publication were skipped. The
focused repair supports both menu patterns and tests an ExpandCollapse-only WPF
peer as well as the ordinary Invoke button. Only this Windows test helper is added
to the explicit macOS runtime-reuse scope; shared OCR and dependency rejection
remain covered. Protected publication remains a separate owner review for the
exact new installer bytes.

The repair's push and PR gates pass, including the new Windows regression fixture.
PR #8 merged at `820a352f5d75216706f0ea35e9622e29a15a7e4c`; corrected
[Release 38889738880](https://github.com/chonnakanch/yomimado/actions/runs/38889738880)
passes planning and is building a fresh candidate. Earlier installer hashes and
unrecorded acceptance are not carried forward. All corrected main
[Checks 38889739313](https://github.com/chonnakanch/yomimado/actions/runs/38889739313)
jobs and the aggregate gate pass.

Before the corrected Windows build completed, follow-up inspection identified
Toggle-only `aria-pressed` scan buttons as another unsupported driver pattern.
The helper now invokes Toggle when Invoke is unavailable, with a real WPF
regression from both pressed states. Menu ExpandCollapse and ordinary Invoke
remain covered; no app/runtime/dependency changes are involved.

PR #9 passed all push/PR checks and merged at
`c03ee1edba4e0f545cb7ed85a7552c544a4bfcdc`. All final main
[Checks 38892964546](https://github.com/chonnakanch/yomimado/actions/runs/38892964546)
pass. The superseded `820a352` build was cancelled; final
[Release 38892964547](https://github.com/chonnakanch/yomimado/actions/runs/38892964547)
passed planning and private input verification before rebuilding both installers.

Final release-build verification is complete: macOS passes in 11 minutes 28 seconds,
Windows in 46 minutes and combined verification in 1 minute 33 seconds. Windows
exact-setup startup/Quit, model setup, scan buttons/shortcuts, cancellation and
frozen learning/persistence all pass. The
[verified candidate](https://github.com/chonnakanch/yomimado/actions/runs/38892964547/artifacts/12045450534)
is retained until 2026-10-30; its ZIP digest and delivery scope are recorded in
[the shared release record](desktop-release.md). Public API metadata confirms the
successful jobs and, at that point, a waiting publisher; the large artifact was
not downloaded locally. The owner subsequently approved publication, as recorded
in Current status. Physical Windows/mixed-DPI checks and a detailed local
installed-app report remain unrecorded; the published tag stays at `c03ee1e`.

### Shared publication environment name — 2026-10-16

The owner requested a platform-neutral approval name. Future release workflows,
private-input protection checks and publisher validation use `desktop-release`
instead of the historical `macos-release`. The replacement retains the existing
required reviewer, disabled administrator bypass and exact `main` deployment rule;
the old protected environment remains for historical runs. Validation rejects the
old name and still rejects missing reviewers, administrator bypass and broad or
tag deployment rules. This changes release workflow metadata, not application
code, dependencies or the published 0.2.0 installers.

The live GitHub environment passes the updated validator. API comparison confirms
identical reviewer identity, self-review setting, administrator bypass and branch
policies; the comparison is retained under ignored
`services/ocr/build/release-environment-rename/`. All 229 release-tool tests, Ruff
lint/format, Prettier and diff checks pass; the develop push CI also passes.

### Windows missing OCR regions — 2026-10-16

The owner reports that 0.2.0 scans finish without boxes in both capture modes,
including after restart. Read with keyboard reports “Show an OCR result before
focusing its regions,” consistent with the stored result not reaching native
interaction setup. Production Capture debug is intentionally absent; do not ask
users to enable a nonexistent Settings control.

The repaired publication path derives its URL from the loaded capture-selector
page, sets the session-specific destination at window creation, and stores OCR
state before the new root can request it. Reused overlays also navigate from this
loaded app URL, avoiding persistence of an initial `about:blank` source. Existing
frame/coordinate mapping, input routing and generation guards remain in place.
Regression cases cover development/macOS/Windows origins and blank-URL rejection.
All 63 native tests and strict Clippy pass locally; native debug compilation passes.
The app version advances to 0.2.1 for a new candidate. This is source verification,
not confirmation that the owner's installed Windows rendering is fixed. New
Windows visual/keyboard verification and protected publication remain pending.

Pre-commit checks also pass all 172 frontend tests, the TypeScript/production
frontend build, all 229 release-tool tests, desktop/document formatting and the
frozen-runtime reuse guard. OCR service/model/dependency inputs are unchanged.

The exact 0.2.1 main Checks and release build/verification now pass. The Windows
installed UI tests cover startup, model setup, scan controls and cancellation;
they do not establish the reported region rendering fix on the owner's hardware.
Both installer candidates and their exact provenance/hashes passed combined
verification. The Windows-only artifact is available for the owner's fresh-launch
check; publication remains waiting in `desktop-release`. Preserve `31f51a7` on
main until review. Local development UI automation was unavailable for the
unbundled Mac process; only its successful launch is recorded, and its test
launcher was stopped without stopping the existing OCR service.

**Owner verification — 2026-10-17:** the exact Windows 0.2.1 candidate from run
`38930205981`, source `31f51a7`, now passes both capture modes and keyboard/popup
interaction by owner report: “Both modes and keyboard work.” The setup hash and
test scope are recorded in [the Windows test record](windows-installed-test.md).
This closes the reported missing-overlay regression on that Windows setup.
Protected publication, exact macOS installer acceptance and untested hardware
cases remain separate; no additional publication approval was supplied.
