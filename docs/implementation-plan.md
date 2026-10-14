# YomiMado — Implementation Plan

## Current status

Updated **2026-10-14**. UI redesign Phases 3 and 4 are accepted. Phase 5 Settings
is implemented for review on tracked `develop`; the app version remains `0.1.0`.

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

### Phase 5 Settings — implemented for review

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

Local verification passed 148 frontend tests in 20 files, TypeScript/production
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

- [ ] Owner acceptance of Phase 5 layout and secondary-window close/reopen behavior.
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
