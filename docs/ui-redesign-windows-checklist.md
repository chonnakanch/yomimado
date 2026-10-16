# Windows UI redesign acceptance checklist

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

## Record the test context

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

## One-monitor checks

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

## Transitions and recovery

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
local. The related [overlay guide](ui-overlay-testing.md) explains debug geometry
and capture-preview options.

## Automated coverage available now

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
