# Retry OCR for one bubble (development source)

Open an existing bubble with an OCR review indicator, then click **Check OCR**.
The existing small indicator opens its review reason and two explicit actions:

- **Retry bubble OCR** captures the current bounds of that region again.
- **Redraw bubble bounds** opens the capture selector so you can draw a tighter
  or corrected rectangle inside the original scanned area. Escape cancels.

Keep the manga page in place. App controls/overlays hide before capture so they
are excluded from the new pixels. The existing local OCR service handles the
crop. This does not automatically translate or save anything, and it adds no
dependency, model, dataset, network OCR provider or continuous scanning.

One successful recognized region replaces the selected region's text, token
data, orientation and polygon; its ID and list position stay the same. All other
regions remain unchanged. The overlay is rebuilt with the original capture
metadata and the updated bubble opens automatically. The toolbar's ordinary
Rescan continues to target the original page/area rather than the small retry crop.

Retrying the same pixels can return the same text. Redrawing is useful when the
original crop missed strokes or included another bubble. Use **Edit OCR text**
for a known text correction. Apply or cancel an open edit draft before retrying.

## Failure, cancellation and uncertainty

Capture failure, unavailable OCR, no text, or multiple detected regions keep
the original result. For multiple regions, redraw tightly around one bubble.
During processing the toolbar retains its existing scan progress/cancel action.
Cancel returns to the previous result, and late replies cannot overwrite it or
a newer scan. A changed display layout requires a new page scan; stale geometry
is not made interactive on a different display configuration.

Rerunning Manga OCR does not establish correctness: its output has no calibrated
recognition-confidence score. Retried regions therefore retain **Check OCR** and
a review reason. A successful retry never claims confidence merely because it ran.

This slice retries existing regions through their review indicator. Adding a
completely missed region without an existing region/indicator is future work.
Redraws outside the original scan are rejected so unrelated results keep the
same capture coordinate space. Demo boundaries cannot start a retry.

## Implementation and verification

The popup receives a native session/region identity. Native code validates the
current popup query, completed scan generation and live display before opening
an ordinary capture session associated with exactly that target. The existing
selector and local OCR request are reused. Replacement uses the native capture's
metadata rather than accepting image dimensions or display offsets from the UI.

The crop polygon is mapped through capture-image coordinates → screen physical
pixels → original-image coordinates. The original overlay metadata remains the
authority for rendering and native hit testing. Native tests cover negative
monitor origins, 100/125/150/200% scaling, differing image/physical dimensions,
redrawn bounds, unchanged sibling regions and failed/stale requests. Session
tests verify cancellation invalidation and preservation of full-page Rescan.
Frontend cases cover both actions, duplicate clicks, edit drafts, errors,
single-region publication, cancellation and reopening only after native reveal.

Windows native/mixed-DPI interaction and exact-installer acceptance remain
separate verification; development-source completion is not installer approval.
