# UI verification and native acceptance

Use this guide for current overlay checks, the Windows hardware matrix and tray
acceptance. The dated redesign review below is historical evidence for its stated
source revisions; it is not a claim that every current native case passed.
Exact installer tests remain in [macOS](macos-clean-mac-test.md),
[Windows](windows-installed-test.md) and [shared release records](desktop-release.md).

- [Charcoal and blue theme](#charcoal-and-blue-theme)
- [Learning popup modes](#learning-popup-modes)
- [Capture shortcut verification](#capture-shortcut-verification)
- [Detector release link verification](#detector-release-link-verification)
- [Completed-overlay hide controls](#completed-overlay-hide-controls)
- [Bubble translation toggle](#bubble-translation-toggle)
- [Horizontal OCR geometry recovery](#horizontal-ocr-geometry-recovery)
- [Native overlay checks](#native-overlay-checks)
- [Windows acceptance checklist](#windows-acceptance-checklist)
- [Tray OCR result restoration](#tray-ocr-result-restoration)
- [Tray verification and acceptance](#tray-verification-and-acceptance)
- [Dated redesign review](#dated-redesign-review)
- [Retained window and debug evidence](#retained-window-and-debug-evidence)

## Charcoal and blue theme

Initial development check — 2026-10-22: browser review with synthetic light and dark
panels covers default, hovered, selected and dashed review OCR outlines, the
bold X control, toolbar actions and the capture drag rectangle. OCR halos use a
separate stroke-only polygon, leaving ordinary interiors transparent and limiting
hover/selection fill to 6%/10% blue. The selector has no full-screen tint; its
rectangle uses a 2 px blue border, thin dark edges and a 6% blue interior.

Computed shared-token contrast across the background, surface and elevated
surface is at least 6.48:1 for normal/muted text and 6.60:1 for links. White labels
on `#0866FF` actions measure 4.82:1, and on the darker hover 6.05:1. Focus indicators
measure at least 6.60:1 against these surfaces. Error and success text retain
separate colors and explicit labels. These measurements cover the declared opaque
UI tokens, not arbitrary manga pixels.

All 318 frontend tests, TypeScript/Vite build and frontend formatting pass.
Follow-up visual review confirms the lighter blue book mark styling, 3 px
selected Settings outline and Sources view without the slogan or Japanese
app-name subtitle. Its source descriptions and licence links remain present.
The 49 app, Settings, toolbar and overlay tests, frontend build and formatting
pass after this refinement. Keyboard-focused OCR strokes use 4 px with a 6 px
dark halo; other control focus rings use 3 px.
Icon follow-up — 2026-10-22: reviewed the blue desktop exports at 32/128 px and
Windows tray mark at 32 px. All PNGs retain RGBA transparency; ICO and ICNS decode
successfully. Tray exports reproduce from their generator and the macOS template
hash is unchanged. Generator lint and the macOS debug build pass. This does not
establish installed Dock/taskbar/menu-bar acceptance for the new exports.

Outline follow-up — 2026-10-22: default OCR strokes use brighter `#0080FF` and
hover uses `#4D9FFF`. Remove the earlier dark halo and its decorative polygons;
OCR regions now render as one polygon each. Review/demo dashes and keyboard focus
remain, while buttons and the capture drag rectangle retain their existing
palette. Synthetic light/dark browser review confirms normal, hovered, selected
and dashed outlines have no dark border. All 45 capture/overlay tests, frontend
build and formatting pass. Earlier halo observations above describe the initial
theme only.

Final palette follow-up — 2026-10-22: primary actions and 2 px OCR strokes now
use `#0080FF`, hover/link uses `#339AFF`, and copper `#D98B5F` is reserved for
identity marks. OCR and capture interiors use 14% blue. Cards have 14 px corners
and 1 px borders. The current copper/blue desktop exports and Windows tray mark
replace the earlier all-blue assets; the monochrome macOS template is unchanged.
The earlier contrast measurements describe the earlier palette, not this update.
Synthetic browser review covers the overflow menu, Settings heading, popup modes,
inside-field editor focus and both disclosure controls without filled hover.
All 324 frontend tests, formatting, TypeScript/Vite and the macOS debug build pass.

Native macOS/WebView and Windows/WebView2 visual acceptance, fractional scaling,
pass-through and exact-installer checks remain unverified for this theme. Follow
the [native overlay checks](#native-overlay-checks), including light/dark pages,
vertical polygons, capture cancellation, hidden capture chrome and Hide/Show.
The theme changes no native window sizes, coordinate transforms or hit geometry.

## Learning popup modes

The Words/Select/Edit redesign is covered by popup regressions for source-preserving
Unicode selection, draft reset/cancel/apply, stale responses, request-only
translation, saved-entry identity, temporary Copied feedback, translation retry,
translation copying and collapse. Browser review uses synthetic text and fake
service/clipboard/storage responses at 420 px and 320 px; it checks the actual
components, pinned sentence actions, saved/retry states and the editor without
confidence underlines. Selection help is a short visible sentence with full
keyboard guidance retained for assistive technology. The focused editor border
stays within the field. Conjugation and compound controls remain readable on
hover and expand/collapse with synthetic data.
All 324 frontend tests, frontend formatting and the TypeScript/Vite build pass;
73 local links/fragments in the affected guides were checked.

IME regression check — 2026-10-23: Escape with `isComposing` or the legacy IME
key code `229` leaves the correction editor, focus and draft intact without
preventing the composition event. The draft can then be applied; ordinary Escape
continues to cancel it. These are DOM event regressions, not native IME acceptance.

This does not establish native WebKit/WebView2 caret/IME, anchored resizing,
focus/pass-through or Windows hardware acceptance. Follow the native overlay
matrix below and verify Words/Select/Edit, cancellation, correction, copy/save,
translation retry and a long sentence in the real app.

## Continuing action/state and desire conjugations

Development check — 2026-10-23: conjugation regressions cover ている／でいる,
casual てる／でる, their plain/polite tense and negative forms, plus たい,
たかった, たくない and たくなかった with optional です. Representative
auxiliary splits were checked using the local pinned Lindera 6.0.0/IPADIC
provider, including the merged てる／でる tokens and dropped-い polite forms.
Tests retain irregular verb classes, exact manual spans, source code-point
offsets, context notes and explicit unsupported auxiliary chains.

The 141 focused conjugation/popup tests pass. Popup regressions verify the
collapsed explanation, the complete 食べてなかった breakdown and dictionary
lookup/save for manually selected 食べたくなかったです, preserving Japanese
source text and making no translation request. All 377 frontend tests,
frontend formatting, TypeScript/Vite and the macOS Apple Silicon debug build
pass. On the local Node 26 runtime, the full suite uses
`NODE_OPTIONS=--no-experimental-webstorage npm test` to let jsdom supply storage;
an initial run without this flag failed in existing storage-dependent tests.
CI pins Node 22.23.2.

These are source/debug checks. Native popup interaction on macOS/Windows,
Windows compilation and exact-installer acceptance were not performed for this
change. The existing disclosure layout and native capture/overlay behavior are
unchanged. Follow the native popup checks above when recording hardware acceptance.

## Local backup and restore

Copy follow-up — 2026-10-23: reduce the panel to one helper sentence, compact
new/duplicate counts and Restore/Cancel controls. Remove the technical footer
and shorten completion feedback. The 13 backup UI tests, frontend formatting and
TypeScript/Vite build pass; browser review uses synthetic data and mocked dialogs.

Development check — 2026-10-23: the Saved disclosure and restore preview were
reviewed in the browser with synthetic saved text and mocked native dialogs/service.
The preview shows new/duplicate counts before confirmation; completion returns
focus to Restore backup and refreshes the list. Frontend regressions cover native
dialog cancellation, duplicate-only previews, duplicate click admission, retry
after storage failure, invalid response handling, search retention, both collections
and refresh deferred until a pending removal finishes.

Service regressions verify portable round trips, Unicode/source text, readings,
meanings, translations, save dates, existing IDs, repeated imports, duplicate
identity, first-entry handling, preview without writes, concurrent saves since
preview, complete-file validation, bounds and request guards. A failing sentence
insert rolls back earlier word inserts. Native file tests verify same-directory
replacement, preserved backups on failure, staging cleanup, UTF-8/size checks and
window authorization.

All 392 frontend, 269 service and 83 native tests pass, along with frontend/Ruff
formatting, Ruff, TypeScript/Vite, Clippy and the macOS Apple Silicon debug build.
Local Node 26 uses `NODE_OPTIONS=--no-experimental-webstorage npm test` for jsdom
storage. No screenshot or user database is used by these tests. Native file-dialog
interaction, Windows compilation/hardware and exact-installer acceptance remain
unverified; the source tests do not establish those passes.

For native acceptance, export from Saved with a search active, cancel both dialogs,
restore into an empty library and repeat the import. Check preview/cancel,
read-only or unavailable destinations, Japanese file paths, existing-backup
replacement and preservation of search, dates, readings and translations. Record
the source, platform and results. The changed Python runtime requires a compatible
reviewed macOS seed before packaging; existing approvals retain their source identities.

## Capture shortcut verification

For configurable bindings, test **Settings → Scan & OCR → Scan shortcuts**:
record both actions, cancel with Escape/Tab/focus/category changes, reject duplicate
or OS-conflicting combinations, restore defaults, restart and verify the saved
pair. Trigger captures from another app and verify the pointer's monitor is used;
old bindings should stop working after replacement. Check a write failure without
losing the old pair and a startup conflict without losing toolbar access.

Development check — 2026-10-21: the native Apple Silicon debug app saved
Option+Cmd+K immediately and rejected assigning the existing Whole Screen chord
to Selected Area, without opening a capture selector. The saved JSON matched the
active pair. The automation service failed during the restart inspection, so
native restart, restore-default interaction and external-app trigger checks were
not verified by that automation attempt. The temporary process/preferences were
removed from active use.
All 301 frontend and 75 native tests pass, including persistence, defaults,
rollback, cancellation and listener lifecycle. Formatting, Clippy and current-target
frontend/native builds pass. Windows interaction and exact-installer acceptance
remain separate.

Owner acceptance — 2026-10-21: the owner subsequently reported “i test manually
and it pass” for the capture-shortcut feature at source
`f65576cbe95609b893061f5fc0144fba6a045156` and requested its PR. This records the reported manual feature pass;
individual cases and hardware/platform coverage were not enumerated. It does not
establish Windows-specific coverage or exact-installer acceptance.

## Detector release link verification

Development check — 2026-10-21: reproduced the unresponsive **original release
page** link in the existing local app bundle. In the fixed Apple Silicon debug
app, **Settings → Scan & OCR → original release page** opened the exact upstream
`beta-0.2.1` release in the default browser (Helium). The debug UI used a temporary
`required: true` detector-status fixture to expose the packaged setup controls;
the actual native browser command was used. The fixture was removed afterward.

Clicking the release's `comictextdetector.pt.onnx` asset completed a 94,669,756-byte
download. Because a copy already existed, the browser named the new file
`comictextdetector.pt (1).onnx`. Both files matched the app's supported SHA-256:
`1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
No model was imported or replaced during this check.

Follow-up — 2026-10-21: changed the destination and link label to **latest release
page**, using `/releases/latest` in both the UI and native launcher. That URL
currently resolves to `beta-0.3`. A separate download through
`/releases/latest/download/comictextdetector.pt.onnx` has the same 94,669,756-byte
size and supported SHA-256 recorded above. The native interaction above used the
earlier fixed tag; this follow-up verifies the latest redirect/download and source
checks. Model import continues to require the supported checksum.

Frontend regressions cover native dispatch, prevention of webview navigation,
browser-launch failure and retry, without triggering model import. All 303
frontend and 75 native tests, frontend formatting/build, Rust formatting, Clippy
and the current-target native debug build pass. Windows browser interaction and
exact-installer acceptance remain unverified; this source fix is unreleased.

## Completed-overlay hide controls

Development source — 2026-10-21: automated checks cover temporary Escape
eligibility/release, protected YomiMado window focus, active scans, stale result
generations, the icon's measured native hit rectangle, duplicate requests and
hide failures. Existing overlay coordinate and click-through regressions pass.
All 306 frontend tests and 79 native tests pass, together with TypeScript/Vite,
Clippy with warnings denied, formatting and the macOS debug build.
The native Apple Silicon debug app starts, but its capture smoke test stops at
the macOS Screen Recording permission gate before creating a demo result.
This does not establish a native Escape/icon interaction pass.

For native acceptance, complete a scan, leave focus in the reader, press Escape,
and restore the retained result with the toolbar toggle. Repeat using the small
X button, including an overlay above/below its selection, a full-screen
capture and Retina/Windows fractional scales. Verify transparent space still
passes reader input. Reopen a popup/menu/Settings and check its ordinary Escape
behavior. Start/cancel/rescan, then ensure a delayed hide request cannot hide the
new result. Windows interaction, registration-conflict behavior and exact
installers remain unverified.

## Bubble translation toggle

Source verification — 2026-10-23: **Translate bubbles** starts off on a completed
scan. Regression coverage checks explicit activation, sequential local requests,
duplicate-text reuse, sound-effect/demo exclusion, review labels, Retina text
bounds, immediate return to Japanese, abort/late-response handling, native
hide/scan cancellation, missing-model error/Retry and provider re-selection.
Fitting stops at 11 px and uses an ellipsis when a complete translation cannot
fit. Popup coverage checks opening the full requested translation without saving
and rejecting late results after editing Japanese. Native tests cover bounded
panel counts and rectangle conversion/clipping at 100%, 125%, 150% and 200%.

Synthetic Chromium and WebKit browser checks use mocked Tauri and translation replies, with ordinary,
narrow/overflowing and narration regions plus an excluded sound effect. They
verify no translation before toggling, three sequential requests/panels, one
overflow marker, five reported native rectangles, full-popup activation and
toggle-off restoration. They establish UI behavior, not model inference quality
or native click-through acceptance.

All 403 frontend and 85 native tests, frontend formatting, TypeScript/Vite,
Rust formatting/Clippy and the macOS debug build pass. The frontend tests use
`NODE_OPTIONS=--no-experimental-webstorage` with the local Node 26 runtime.
No service source, dependencies or model resources change.

Native macOS/Windows interaction and actual model inference in this mode remain
unverified. Check both supported systems with a configured local model: toggle
while translation is pending, hide/restore and rescan, missing-model Retry,
long/tiny/angled/review regions, keyboard navigation and popup return. Verify
panel corners remain visible/clickable on Windows, surrounding artwork remains
click-through, and mixed-DPI/negative-origin monitors preserve alignment. OCR
text bounds may not fill the bubble interior; this feature does not segment
bubbles or accept a new installer.

Overflow follow-up — 2026-10-24: an owner screenshot showed many complete
translations hidden behind ellipses. Long translations now retain visible text
and scroll from the first line, with space reserved for the scrollbar. Narrow
panels widen within capture/neighbor limits; English uses word wrapping and
hyphenation. The HTML text surface accepts scrolling and clicks, and mirrors
review/selection borders while original polygons retain keyboard navigation.
Four layout regressions cover edge bounds, neighboring-panel separation, existing
overlaps and separate rows. The component regression keeps full overflow text
visible at 11 px and checks popup activation. A browser check of the actual
frontend with five synthetic regions and mocked native/translation replies
confirms visible first lines and scrolling to the final line of a long paragraph.
All 407 frontend tests, frontend/document formatting, TypeScript/Vite and the
macOS debug app bundle build pass; 216 local documentation links/fragments pass.
This does not establish native Windows scrolling or a new installer pass.

## Horizontal OCR geometry recovery

Development source — 2026-10-22: model-free regressions cover light/dark paragraph
rows at 1×/2×, truncated title continuation, neighboring-column boundaries, rotated
polygon clipping, source ordering, nested fragments and bounded crop counts.
216 service/benchmark tests, 318 frontend tests, Ruff, frontend formatting,
TypeScript and the frontend build pass. The existing 13-image synthetic benchmark
and four new clean cases were compared with the Windows ONNX source components
on macOS; [measurements and limitations](ocr-geometry-results.json) retain accuracy,
model-call counts and scan time. Supplied screenshots stayed private and local.

Mixed-content follow-up — 2026-10-22: 16 additional model-free regressions cover
identical glyph rows with/without a non-Japanese label at 1×/1.5×/2× on light/dark
backgrounds, nearby genuine vertical text, separate columns, same-baseline labels,
failed row recognition, uncovered glyphs, padded duplicates and tile/mask retries.
225 service tests, seven benchmark-metric tests, Ruff, 318 frontend tests,
TypeScript and the frontend build pass. Nine clean context variations and the
annotated attachment were checked locally with Windows ONNX source components on
macOS. The Japanese row outlines agree across the clean header controls; Thai
recognition remains unsupported and carries a warning when the detector classifies
it as non-Japanese. [Mixed-content measurements](ocr-mixed-text-results.json)
record the geometry outcomes, older fixture comparison and limits.

Coverage/warning regression check — 2026-10-23: model-free tests retain a fragment
with extra visible glyphs despite more than 60% box overlap, across full/tile/mask
passes and light/dark backgrounds. Covered duplicates still skip recognition.
Whole-selection and expanded short vertical recovery retain the detector's
non-Japanese warning alongside the recovery reason and original diagnostics.

For native acceptance, repeat Selected Area and Whole Screen on the Windows laptop
and extended monitor, including differing display scales and reversed monitor
origins. Use a large horizontal title and separate paragraphs on light/dark pages.
Verify complete title text, separate row targets, no nested click targets and
no polygons outside the selected image. Repeat identical Japanese with a blank,
Thai and English header, then tight and expanded selections on both sides of the
800-pixel retry threshold. Check that false vertical targets do not return and
that non-Japanese warnings remain isolated from Japanese rows. Test vertical/rotated text, close columns
and artwork negatives too. Native Windows interaction and new exact installers
remain unverified; source inference does not establish hardware acceptance.

## Native overlay checks

This development-only check uses synthetic Japanese text and ordinary browser
controls. No manga image, model download or service/API change is needed.

Run the existing local OCR service with its configured offline models, then run
`rtk npm run tauri -- dev --no-watch` from `apps/desktop`. Open
`http://localhost:1420/src/features/overlay/fixtures/reader.html` in Safari or a
Windows browser. The fixture is not a production Vite entry or public asset.
On macOS, grant capture access to the actual development launcher when required;
this session used normal command-based development after temporary ad-hoc bundles
proved inconvenient for repeated grants.

### Check the native interaction

1. Whole Screen detects/crops the manga page/spread before OCR; menu-bar, browser
   tabs/address and surrounding app text must not become OCR regions. When the
   boundary is uncertain, verify saved-area reuse, then missing/invalid saved-area
   drawing and cancellation. Selected Area still scans exactly what is dragged.
   In Selected Area and the Whole Screen manual fallback, right-click before and
   during a primary-button drag, including releasing either button first. No
   context menu or OCR should open; the interrupted rectangle clears and a new
   primary-button drag must work. Check macOS Control-click too, then Escape and
   a fresh capture. Repeat after pointer cancellation or loss of pointer capture.
   Right-click Settings, Saved, the toolbar, learning popups and OCR overlays;
   none should open the browser context menu.
   Whole Screen and Selected Area produce aligned polygons for the horizontal and
   vertical fixture text. Switch from Whole Screen to a smaller Selected Area, then
   select a different-size area and use Rescan and Hide/Show. All polygon edges must
   remain visible: establish the target monitor, resize, then reapply the position
   of the reused overlay. Also verify the first Retina scan's physical window size.
   Capture must exclude the toolbar, result and popup. Check the leading `一` and
   ending `。` of the horizontal sentence and the outer strokes of both vertical
   columns. Compare a tight reader-panel selection, a whole-display manual selection
   and the Whole Screen button: downsampled detection must not lose a disconnected
   leading thin stroke. Image-derived boundary corrections use dashed approximate/review
   regions; their popup must retain the original Japanese and review guidance.
   On Windows, start fresh and complete both capture modes: the first overlay
   must render without toggling visibility or performing another scan. Verify
   Read with keyboard immediately, then repeated scans and Hide/Show. The new
   overlay must load the app page even when WebView2 initially reports
   `about:blank`; OCR state must exist before React requests it.
   With a visible Windows taskbar, verify automatic detection stops at the
   monitor's reported work-area edge and never creates regions for its icons,
   clock or weather. Repeat with a light/dark taskbar and any supported taskbar
   edge, then on a secondary monitor at a different scale. Auto-hidden taskbars
   use the work area reported by Windows. Manual Selected Area remains exact.
   Start a fresh app process and choose Whole Screen **before** any Selected Area
   scan. Repeat with cold local models: recognition must complete while the capture
   selector stays hidden, without bringing it to the foreground. A stalled OCR
   upload or response must end with an error after three minutes. Native logs show
   session-bound OCR stages (`Requesting`, `Recognized`, `Publishing`) without
   screenshot bytes or recognized text. Restart the app when testing a native
   scheduling change; frontend hot reload alone does not apply it.
2. With the overlay visibly present, click **Test reader click**, drag-select the
   input text and scroll in the blank side margin. The browser must receive them.
   Start a drag outside a polygon and cross it; verify mouse-up stays with the browser.
3. Hover a polygon, then activate it explicitly. Hover must not perform dictionary,
   tokenization or translation work. A click opens the existing learning popup.
4. Choose **Read with keyboard** in toolbar overflow. Arrows/Home/End change focus;
   Enter/Space open a popup, and Escape returns to its originating region. Escape
   in region navigation hides results; Show restores them without another OCR call.
   Clicking elsewhere dismisses the popup without moving focus back to the overlay.
5. Read with keyboard is disabled without a visible completed result and during
   scans. Settings → Reading explains the controls; no old toggle or Previous/Next
   text panel remains. Keyboard entry must work without moving the pointer over
   a polygon. Navigation must not perform OCR or translation.
6. Rescan, cancel, hide/show and close/reopen must not retain stale hit polygons.
   Disconnect/change a monitor or its DPI; stale geometry must hide with guidance.
7. Try fast pointer entries and immediate clicks at multiple speeds. Record missed
   clicks and response latency; the macOS 8 ms sampler is a fallback and its interval
   is not a measured end-to-end latency guarantee. Measure active/idle app CPU.
8. Repeat on Windows (100%, 125%, 150%, 200%), Retina and mixed-scale monitors,
   including a negative monitor origin. Check window-region clipping/focus borders
   and actual browser input rather than relying only on SVG pointer events.

### Adapter and evidence limits

Windows uses the union of the original polygons and any measured navigator control
bounds through native `SetWindowRgn`; owned GDI handles are released on failure.
macOS uses read-only Quartz cursor/button state and whole-window mouse ignore.
It samples at 8 ms while active, 80 ms while disabled, and preserves the recipient
of a held drag. No event tap, replay, Accessibility/Input Monitoring grant or new
native dependency was added. The native physical transform matches the same OCR
image/selection ratios used by the frontend, including an OS-adjusted client origin.

Recorded evidence and open acceptance gates are in
[dated redesign review](#dated-redesign-review).
Source builds/tests are distinct from native manual checks and installer acceptance.
The [Windows redesign checklist](ui-testing.md#windows-acceptance-checklist) records scale,
multi-monitor, secondary-window and recovery cases for the current development UI.

For frame diagnosis only, set `YOMIMADO_OVERLAY_GEOMETRY_DEBUG=1` when launching
the debug app. Each reveal writes capture metadata, measured native frame and OCR
polygons to stderr; navigator updates also report CSS viewport and physical window
dimensions. It omits screenshot bytes and recognized text, is off by
default and is excluded from release builds. Compare the measured window bounds
with the selected physical rectangle when investigating clipped edges.

## Windows acceptance checklist

Status: prepared on 2026-10-15. The owner chose automated coverage and a checklist
for later interactive verification. No interactive Windows result is inferred
from the macOS workspace or GitHub's Windows Server build runner.

Automated update — **2026-10-16**: final 0.2.0 source `c03ee1e` passes
[Checks](https://github.com/chonnakanch/yomimado/actions/runs/38892964546) and the
[installed Windows release checks](https://github.com/chonnakanch/yomimado/actions/runs/38892964547).
Invoke/ExpandCollapse/Toggle regression coverage, exact-setup startup/Quit,
Settings close retaining the toolbar, model setup, scan buttons/shortcuts, cancellation and frozen
learning/persistence pass. These hosted results do not complete the physical
scale/monitor matrix or the detailed manual cases below. Those remain **not run**.

This checklist tests the redesigned development source. The published v0.1.0
installer and its historical acceptance records describe an earlier UI. No new
installer build, publication or approval is required by this checklist.

### Record the test context

- Source commit: __________
- Windows version/build: __________
- WebView2 version: __________
- Monitor resolutions, scaling and arrangement (including left/above primary): __________
- OCR service/model configuration: __________
- Overall result and failed case IDs: __________

Use the existing [development setup](development.md) with local OCR models and
service available. Launch the current desktop source, and open the repository's
synthetic reader in a browser:

```text
http://localhost:1420/src/features/overlay/fixtures/reader.html
```

Use synthetic or private local images for page/spread checks. Do not add manga
screenshots to the repository. Record unsupported hardware cases as **not run**.

### One-monitor checks

Run cases W1–W7 at each available scale, restarting the desktop app after changing
scale so a fresh-process result is recorded. Start W1 before any Selected Area scan.

| Scale | W1      | W2      | W3      | W4      | W5      | W6      | W7      |
| ----- | ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| 100%  | not run | not run | not run | not run | not run | not run | not run |
| 125%  | not run | not run | not run | not run | not run | not run | not run |
| 150%  | not run | not run | not run | not run | not run | not run | not run |
| 200%  | not run | not run | not run | not run | not run | not run | not run |

| ID  | Action and expected result                                                                                                                                                                                                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1  | On a fresh launch, use Whole Screen first. Recognition completes, the active scan button shows progress, and OCR polygons appear. Confident detection crops the page/spread and excludes browser/menu text. Uncertain detection uses the saved-area/draw fallback rather than recognizing the entire monitor. Repeat once with cold local models. |
| W2  | Compare a tight Selected Area, a whole-monitor manual selection, and Whole Screen on the same text. All detected outlines align with their characters, including leading `一`, ending `。` and both vertical columns. Review regions retain their dashed outlines. Rescan uses fresh pixels from the previous successful area.                    |
| W3  | Click and scroll outside polygons, select browser text, and drag from a blank margin through a polygon. Input and mouse-up stay with the browser. Click a polygon explicitly to open the learning popup; hover alone does not run learning requests.                                                                                              |
| W4  | Choose More actions → Read with keyboard. Arrows/Home/End select regions, Enter/Space opens a popup, Escape returns to its region, and another arrow still works. Escape in region navigation hides the overlay. Show restores it without another OCR request.                                                                                    |
| W5  | Place the toolbar near the bottom edge. More actions opens above without moving the toolbar or flickering. Mouse opening has no blue focus ring; arrow navigation has an inset ring. Escape/outside click dismisses it. Collapse/expand keeps controls on one row at the same size.                                                               |
| W6  | Open a popup near each screen edge. Long text, dictionary senses and Example compounds remain reachable by scrolling. Edit OCR text → Cancel restores focus. Clicking the browser dismisses the popup without returning focus to the overlay.                                                                                                     |
| W7  | Open Saved, Settings and Sources together. Each has its own content. Close each using native X while the others remain open, then reopen it from the toolbar. The toolbar and OCR session stay running. Repeat the sequence to catch stale/duplicate window labels.                                                                               |

### Transitions and recovery

- [ ] **Saved search and dictionary layout:** search a saved word by Japanese,
      reading (both hiragana and katakana), meaning and source text; search
      sentences by Japanese and saved English. Check that each tab remembers its
      query after reopening, Clear/Escape restores all entries, and IME Escape
      does not interrupt composition. Refresh retains the query and failed
      refresh retains the previous results. At narrow sizes and larger text,
      headwords/meanings stack and source/date/attribution remain reachable.
      Removing a filtered entry still requires confirmation and keeps other
      entries. Record the tested source and scales; browser checks alone do not
      establish native Windows acceptance.
- [ ] **W5 menu sizing regression:** at each scale above, open/close More actions
      repeatedly after a fresh launch. With tray recovery available, all six rows
      include Hide Toolbar and Quit; without it, only Hide Toolbar is omitted.
      Verify no row-count/height cycling. On a short work area the menu scrolls,
      End reaches Quit, Home returns to the first enabled action, and Escape closes.
- [ ] **W8 — Mixed DPI:** with two differently scaled monitors, move the toolbar
      to each, scan there and repeat W3–W7. Toolbar buttons target its monitor;
      shortcuts target the monitor under the pointer. Record both scales and origins.
- [ ] **W9 — Negative origins:** place the secondary monitor left of, then above,
      the primary. Scan and open edge popups on it. OCR outlines, hit targets, menus
      and popup bounds remain aligned and on the intended monitor.
- [ ] **W10 — Stale geometry:** while results are visible, change the target
      monitor's scale/resolution or disconnect it. Stale OCR hit targets are disabled
      and guidance appears. Choose a new valid capture target; a fresh scan restores
      aligned regions. Old Rescan geometry must not silently apply to the new layout.
- [ ] **W11 — Cancel/retry:** cancel a selection, then cancel while OCR is pending.
      If the old worker is still finishing, an immediate retry reports busy rather
      than overlapping model work. Retry after it finishes: the new scan works,
      and a late old response cannot replace it. Temporarily stop
      the development OCR service and scan: an error becomes available through the
      toolbar status control; it must not spin indefinitely. Restore the service and
      retry. A stalled upload/body has the existing three-minute deadline.
- [ ] **W12 — Quit:** More actions → Quit closes the development desktop process
      and unregisters its shortcuts. Reopen normally. The separately launched
      development OCR service is intentionally left running; bundled-service cleanup
      belongs to a future explicitly authorized installer/runtime check.

For a failure, record its case ID, source commit, scale/monitor arrangement,
expected versus actual behavior and metadata-only native log. Keep screenshots
local. The related [overlay guide](ui-testing.md#native-overlay-checks) explains debug geometry
and capture-preview options.

### Automated coverage available now

Checks builds and tests the native app on Windows and macOS and runs strict
Clippy with warnings denied on both. Shared tests cover coordinate transforms and
hit polygons at fractional scales/negative origins, menu placement, stale display
rejection, and all 16 transitions among 100/125/150/200% for the overlay frame
guard, including moved/clipped frames. Frontend tests cover keyboard entry/return,
menu failure reporting, independent routes and stale responses.

The shared Windows smoke driver also runs against synthetic WPF windows in CI.
It exercises PID-scoped discovery (including a toolbar absent from the taskbar),
button/menu invocation, Settings native close/reopen and explicit Quit. Service
tests cover exclusive recognition admission and its lifetime across cancellation.

These tests establish calculations and application state behavior. They do not
establish actual WebView2 input routing, physical mixed-DPI transitions or installer
acceptance. Record those results above when a Windows desktop is available.

## Tray OCR result restoration

Development source — 2026-10-22: all 80 native tests, Rust formatting, Clippy with
warnings denied and the macOS debug build pass. The lifecycle regression covers
startup/no completed result, visible results, hidden retained results, cleared
results, capture in progress, cancellation, late cancelled capture updates and a
new completed result. The existing menu routing test includes the scoped restore
ID. The debug app starts successfully; a completed-result restore through the
native tray has not been verified by UI automation.

For native acceptance on macOS and Windows, complete a synthetic scan, hide its
outlines with Escape/X and hide the toolbar. Open the tray menu and choose
**Show OCR results**. Verify the same outlines reappear, the toolbar stays hidden,
reader focus is retained and no OCR request runs. The item should then be disabled.
Repeat after cancellation, errors and a newer scan; it must remain disabled during
capture and when no retained result exists. Check display-disconnect/scale-change
errors and repeat queued clicks without reloading a visible result. Existing
Windows left-click toolbar recovery, right-click menus, quit and native input
routing remain separate acceptance cases. Windows interaction and exact-installer
acceptance are unverified for this feature.

## Tray verification and acceptance

Recorded source verification on 2026-10-17: 70 native and 177 frontend tests
pass, along with strict Clippy, Cargo formatting, frontend Prettier/type/build
checks, the icon generator's Ruff checks and the macOS debug app bundle build.
The macOS debug smoke confirms normal startup, the overflow Hide Toolbar action
and hint, successful hiding, and OS Quit. The UI automation surface could not
expose the native status item for menu-click/restore verification. This debug
bundle does not run the frozen OCR service; installed cleanup is unverified.
The acceptance matrix below remains a checklist, not a report of passing cases.

The [tray source/license review](../THIRD_PARTY_LICENSES/system-tray-review.md)
records the unchanged package graph and complete local macOS Rust notices.

The first hosted source run passed macOS and frontend/service/release-tool jobs,
but Windows tests exited before execution with `STATUS_ENTRYPOINT_NOT_FOUND`.
The native menu imports require Common Controls v6. `build.rs` now embeds the
equivalent default Windows manifest through the MSVC linker for every artifact,
including unit tests, and disables Tauri's binary-only manifest resource to
avoid duplication. This follows the
[upstream diagnosis](https://github.com/tauri-apps/tauri/issues/13419) and keeps
the same app manifest dependency. The
[repaired Checks run](https://github.com/chonnakanch/yomimado/actions/runs/38995496517)
passes at source `74bb75e`, including both platforms' native lint/tests/debug
builds and the Windows synthetic UI-driver check. Frontend, service, release
tools and the final required gate also pass. The original failed run is retained
as evidence; installed/native-interaction acceptance remains separate.

Automated checks should cover menu ID routing, visibility labels, active-scan
guards, idempotent show, tray-failure fallback and disconnected-display recovery.
Extend meaningful existing geometry tests for mixed scales and negative monitor
origins. Test the frontend Hide Toolbar action and error feedback. Avoid tests
that only repeat the menu declarations.

Run native tests, Cargo formatting and strict Clippy on the changed native code;
run relevant frontend tests, typecheck, Prettier and production build after the
overflow-menu change. Require macOS and Windows native CI builds. Native menu
appearance, OS input and actual process cleanup also need installed-app checks:

| Check      | macOS Apple Silicon                                                  | Windows 11 x64                                                      |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Launch     | One legible menu bar icon; toolbar visible                           | One legible notification-area icon; toolbar visible                 |
| Input      | Native menu opens and keyboard navigation works                      | Left-click restores; right-click menu and keyboard navigation work  |
| Recovery   | Hide/show preserves toolbar layout; recover after display disconnect | Same, including overflow area and scaled/secondary displays         |
| Busy state | Tray cannot interrupt capture; actions recover after cancel/error    | Same; no toolbar/menu captured in scan output                       |
| Windows    | Saved/settings/sources reopen correctly after close                  | Same                                                                |
| Quit       | Tray/toolbar/OS Quit exit and stop bundled OCR                       | Tray/toolbar/OS quit routes exit and terminate the service job/tree |
| Appearance | Light/dark menu bar and Retina                                       | Light/dark taskbar and 100%/125%/150%/200% scaling                  |

Verify hotkeys with the toolbar hidden, overlays remaining interactive, repeated
hide/show cycles, and quitting while OCR is active. Check for duplicate icons
after those operations and after a clean relaunch. Exercise Windows Explorer
restart recovery; if the pinned tray stack fails to restore its icon, resolve
that before calling the Windows feature complete.

Source checks establish implementation readiness only. Any future release needs
fresh installer hashes and the applicable exact-installer checks in
[desktop-release.md](desktop-release.md). Installer approval and publication
remain separate owner actions; retain all existing candidate evidence.

## Dated redesign review

Status: **Implementation closed by the owner on 2026-10-16.** Final source
`cd2d202` passes all jobs and the aggregate gate in
[Checks run 38837880179](https://github.com/chonnakanch/yomimado/actions/runs/38837880179).
The remaining acceptance boundaries below are retained for future release work.

Reviewed on 2026-10-15, starting from `0d2c1d0` on `develop`, with the owner's
subsequent request to remove lint exceptions and prepare Windows coverage. This is
source verification after the owner's Phase 5 approval, without a version change or
installer publication.

### Review findings

#### Fixed: More actions could hide a destination failure

The popover dismisses itself before opening Saved, Settings, Sources or keyboard
reading. If the subsequent native command failed, its catch handler rendered the
error inside the hidden popover. The user received no visible failure indication.

The menu now sends failures to the toolbar through a targeted Tauri event. The
existing status icon and accessible alert retain the error, and the status details
show its message on request. Menu placement, focus behavior and successful actions
are unchanged. Two regression tests cover the failure handoff and its presentation
after dismissal. The menu-side test failed against the previous implementation.
Existing core event permissions already permit this handoff.

#### Resolved: strict native lint findings

Clippy found one unnecessary return in macOS pointer-display selection and two
eight-argument IPC commands. The return was removed. The initial review used two
narrow argument-count expectations; the owner then requested a refactor, and both
expectations are now removed. Overlay controls obtain the app handle from their
injected window. The translation popup obtains demo/manga mode from the stored
native OCR result instead of a redundant frontend flag. Each command has seven
parameters, and coordinate and focus behavior remain unchanged.

The native CI matrix now installs Clippy and runs it for all targets with warnings
denied on both macOS and Windows. A shared native regression test exercises all
16 scale transitions among 100%, 125%, 150% and 200%, plus shifted/clipped frames
at negative origins. The existing stale-frame guard is unchanged in behavior and
is now directly tested; a DPI change invalidates old hits even with unchanged
physical window dimensions.

The first strict Windows run also exposed dead code: macOS pointer-sampling
fields/helpers and bundled-service startup plumbing were compiled into Windows
development targets that cannot use them. These now have explicit platform/build
conditions, without warning suppression. Release service startup/cleanup retain
their existing code and configuration. The Windows service module still compiles
under tests, preserving its real SDK-layout, job-termination and readiness tests.

At the initial review, no additional confirmed correctness defects were found in the reviewed capture
session/cancellation, overlay publication/input routing, popup request invalidation,
Saved list/delete lifecycle, model setup, or OCR geometry-extension paths. This is
a focused review of the redesign and its integration boundaries, not a claim that
all application or platform behavior has been proven.

#### Fixed: concurrent OCR requests shared model state

A follow-up review confirmed that overlapping requests could initialize two model
pairs or enter the same detector concurrently. Canceling a desktop request does
not guarantee its inference worker has stopped. The service now admits one
recognition worker at a time, including model initialization, and rejects overlap
with HTTP 503 and `Retry-After: 1`. The lock belongs to the worker and is released
only after recognition finishes or fails; there is no waiting screenshot queue.
Four regression cases cover overlap, cancellation, and recovery after both input
and model errors. The overlap and cancellation cases failed before the fix.

#### Fixed: Windows installed smokes targeted the previous UI

The release UI smoke now discovers the toolbar, More actions and Settings windows
by owned process and title. It uses Selected Area / Whole Screen and the selector's
edge hint. Model import remains scoped to Settings, and native Settings close must
leave the toolbar alive. Both installed smoke scripts now invoke More actions →
Quit YomiMado before checking exit, instead of treating native close as Quit.
Bundled-service identity, child cleanup, port release and model-hash checks remain.

A shared Windows PowerShell 5.1 driver supports button and menu-item automation.
Checks CI runs it against two synthetic WPF processes with identical window
titles, verifying PID isolation, a taskbar-skipping toolbar, Settings close/reopen,
and explicit Quit. This validates the driver without building an installer; it
does not establish installed Tauri UI or physical mixed-DPI acceptance.

### Completed local checks

| Area          | Result                                                                                                                                           |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Frontend      | 172 tests in 20 files; TypeScript; normal and capture-debug production builds; full desktop Prettier check                                       |
| Native macOS  | 60 tests with all targets; locked debug build; Cargo formatting; strict Clippy for all targets with warnings denied                              |
| OCR service   | 97 tests, zero failures/errors/skips; Ruff lint and formatting for app, tests and all packaged entrypoints/backend; dependency consistency check |
| Release tools | 229 unittest checks; Ruff lint and formatting across scripts                                                                                     |
| Patch         | `git diff --check`                                                                                                                               |

Native checks used Rust 1.98.1. The complete service and release-tool suites used
the existing Python 3.11.17 environment, matching the project's CI interpreter.
The first service attempt used the older local `.venv` (Python 3.9): 92 tests
passed and the Windows graph verifier test failed because `hashlib.file_digest`
is a Python 3.11 API. Rerunning the entire suite with 3.11.17 passed all 93 tests;
no compatibility shim, skipped test, model download or dependency change was used.
OCR tests ran with Hugging Face and Transformers offline flags enabled.
The follow-up reran all 97 service tests and 229 release-tool tests, service/script
lint and formatting, and workflow formatting. On 2026-10-16,
[Checks run 38836706682](https://github.com/chonnakanch/yomimado/actions/runs/38836706682)
passed for `e0ebe97`: frontend, service, release tools, strict Clippy, native tests
and debug builds on macOS/Windows, and the synthetic Windows UI driver test.
The aggregate gate also passed. No release workflow was dispatched.

### Remaining acceptance boundaries

- Local compilation/tests cover macOS. The initial review's
  [Checks run 38744718738](https://github.com/chonnakanch/yomimado/actions/runs/38744718738)
  passed frontend, service, release tools and macOS/Windows native tests/builds
  for `0fbb89d`. The follow-up adds strict Clippy to both native CI jobs.
  The owner chose automated coverage and a
  [Windows checklist](ui-testing.md#windows-acceptance-checklist) for later interactive
  Windows/mixed-DPI verification; those manual results remain unrecorded.
- The new error handoff has automated component coverage and verified permissions,
  but no deliberate native window-creation failure was injected into the owner's
  running reading session.
- Automated service tests exercise API, geometry, security, dictionaries and
  persistence with test inputs. They do not repeat the owner's live manga-model
  inference or certify recognition accuracy on arbitrary manga.
- Native close/reopen, simultaneous secondary windows, multi-monitor/Spaces and
  Quit/service-cleanup acceptance retain the separate checklist in
  [retained window and debug evidence](#retained-window-and-debug-evidence). Vorssaint's external
  quit-on-close behavior and the owner's exception choice are unchanged.
- No installer, frozen OCR runtime or release artifact was rebuilt or approved.
  The OCR service source changed in the follow-up. A future macOS frozen-runtime
  seed must be refreshed and reviewed before packaging; the existing source/seed
  mismatch rejection is preserved.

The review left the running development app, OCR service and user-local design
references in place. No new phase or unrelated refactor was started.

## Retained window and debug evidence

On 2026-10-15 the owner approved Phase 5 Settings at application source `9726dc1`
with documentation at `96b9356`. Independent Saved, Settings and Sources windows
retain native title bars and close-to-hide behavior. A quit-on-close utility
(Vorssaint) caused the owner's process exit; native controls were restored at the
owner's request. Programmatic close tests did not establish native-button behavior.
Simultaneous windows, native-button close/reopen, Spaces/multi-monitor behavior
and Windows/mixed-DPI input remain explicit interactive checks. Source approval
alone does not record those cases as passed.

The owner confirmed the Compact popup's layout, screen bounds and keyboard focus
return on macOS on 2026-10-14. On 2026-10-15, native capture at source `9726dc1`
with `VITE_CAPTURE_DEBUG=1` reached the held preview. The owner confirmed Geometry
and Detector disclosures, Show overlay and debug hover tooltips; native logs also
recorded the manga overlay reveal. Automatic page detection was uncertain and
reused the saved-area fallback, so this did not prove automatic crop coverage.
Normal-mode hover suppression has automated coverage; Windows/mixed-DPI debug
interaction remains unrecorded.

For the complete per-attempt history, retrieve
`rtk git show a5f7ebc:docs/implementation-plan.md`. Retain failed attempts and
platform limits when recording a later success; do not infer exact-installer
acceptance from these development checks.

## Translation model verification — 2026-10-18

Source checks cover import validation, persistence, failed-import recovery,
provider snapshots/cache separation, explicit downloads, Ollama progress/retry,
local-only requests and rejection of cloud aliases. The UI checks cover folder
selection/cancellation, import failure, saved selections and explicit Ollama
download/activation. A macOS source smoke imports the existing real Marian model,
translates a synthetic sentence and verifies cache reuse after switching away and
back. The ONNX CPU import/inference/cache path also passes on macOS; this is not
native Windows acceptance. Evidence is kept privately in
`services/ocr/build/resource-reduction-20261018/model-choice-smoke.json` and
`model-choice-smoke-onnx.json`.

Ollama is not running on the development machine: API behavior uses controlled
test responses, and the UI's missing-service guidance is checked live. Actual
Ollama model inference/download and native Windows installed acceptance remain
unverified. These are source changes; no installer or model component is published.
