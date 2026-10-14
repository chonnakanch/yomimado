# Phase 2 native overlay checks

This development-only check uses synthetic Japanese text and ordinary browser
controls. No manga image, model download or service/API change is needed.

Run the existing local OCR service with its configured offline models, then run
`rtk npm run tauri -- dev --no-watch` from `apps/desktop`. Open
`http://localhost:1420/src/features/overlay/fixtures/reader.html` in Safari or a
Windows browser. The fixture is not a production Vite entry or public asset.
On macOS, grant capture access to the actual development launcher when required;
this session used normal command-based development after temporary ad-hoc bundles
proved inconvenient for repeated grants.

## Check the native interaction

1. Whole Screen and Selected Area produce aligned polygons for the horizontal and
   vertical fixture text. Switch from Whole Screen to a smaller Selected Area, then
   select a different-size area and use Rescan and Hide/Show. All polygon edges must
   remain visible: macOS resizing must precede positioning the reused overlay.
   Capture must exclude the toolbar, result and popup.
2. With the overlay visibly present, click **Test reader click**, drag-select the
   input text and scroll in the blank side margin. The browser must receive them.
   Start a drag outside a polygon and cross it; verify mouse-up stays with the browser.
3. Hover a polygon, then activate it explicitly. Hover must not perform dictionary,
   tokenization or translation work. A click opens the existing learning popup.
4. Choose **Focus regions** in toolbar overflow. Arrows/Home/End change focus;
   Enter/Space open a popup, and Escape returns to its originating region. Escape
   in region navigation hides results; Show restores them without another OCR call.
   Clicking elsewhere dismisses the popup without moving focus back to the overlay.
5. Switch the optional estimated-order setting on/off; its controls remain usable
   and its native hit rectangle must not cover the rest of the reader.
6. Rescan, cancel, hide/show and close/reopen must not retain stale hit polygons.
   Disconnect/change a monitor or its DPI; stale geometry must hide with guidance.
7. Try fast pointer entries and immediate clicks at multiple speeds. Record missed
   clicks and response latency; the macOS 8 ms sampler is a fallback and its interval
   is not a measured end-to-end latency guarantee. Measure active/idle app CPU.
8. Repeat on Windows (100%, 125%, 150%, 200%), Retina and mixed-scale monitors,
   including a negative monitor origin. Check window-region clipping/focus borders
   and actual browser input rather than relying only on SVG pointer events.

## Adapter and evidence limits

Windows uses the union of the original polygons and any measured navigator control
bounds through native `SetWindowRgn`; owned GDI handles are released on failure.
macOS uses read-only Quartz cursor/button state and whole-window mouse ignore.
It samples at 8 ms while active, 80 ms while disabled, and preserves the recipient
of a held drag. No event tap, replay, Accessibility/Input Monitoring grant or new
native dependency was added. The native physical transform matches the same OCR
image/selection ratios used by the frontend, including an OS-adjusted client origin.

Recorded evidence and open acceptance gates are in
[implementation status](implementation-plan.md#ui-redesign--phase-2-review).
Source builds/tests are distinct from native manual checks and installer acceptance.

For frame diagnosis only, set `YOMIMADO_OVERLAY_GEOMETRY_DEBUG=1` when launching
the debug app. Each reveal writes capture metadata, measured native frame and OCR
polygons to stderr. It omits screenshot bytes and recognized text, is off by
default and is excluded from release builds. Compare the measured window bounds
with the selected physical rectangle when investigating clipped edges.
