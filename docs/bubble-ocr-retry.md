# Retry OCR for one bubble (development source)

Open an existing bubble with an OCR review indicator, then click **Check OCR**.
The existing small indicator opens its review reason and two explicit actions:

- **Retry bubble OCR** captures the current bounds of that bubble again.
- **Redraw bubble bounds** opens the capture selector so you can draw a tighter
  or corrected rectangle inside the original scanned area. Escape cancels.

Keep the manga page in place. App controls/overlays hide before capture so they
are excluded from the new pixels. The existing local OCR service handles the
crop. This does not automatically translate or save anything, and it adds no
dependency, model, dataset, network OCR provider or continuous scanning.

One bubble can produce several detected text regions. A successful retry keeps
each part's text, tokens, orientation and polygon, replacing the selected region
with those parts at its original list position. The first part retains the
selected ID and opens automatically; additional parts receive unique IDs and
remain individually clickable. Unrelated regions remain unchanged. The overlay
is rebuilt with the original capture metadata. The toolbar's ordinary
Rescan continues to target the original page/area rather than the small retry crop.

Retried parts share a native `retryGroupId`. Retrying any part recaptures their
combined bounds and replaces the whole group, so another retry/redraw does not
leave duplicate old fragments. All replacement geometry is validated before any
of the previous regions are replaced.

Retrying the same pixels can return the same text. Redrawing is useful when the
original crop missed strokes or included another bubble. Use **Edit OCR text**
for a known text correction. Apply or cancel an open edit draft before retrying.

## Failure, cancellation and uncertainty

Capture failure, unavailable OCR, no text, or an invalid detected region keeps
the original result. Multiple valid regions inside one bubble are accepted.
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
single/multiple-region publication through retry and redraw, cancellation and
reopening only after native reveal. Native cases also cover unique IDs, repeated
group retries, preservation of individual tokens/polygons, and atomic failure.

Windows native/mixed-DPI interaction and exact-installer acceptance remain
separate verification; development-source completion is not installer approval.
