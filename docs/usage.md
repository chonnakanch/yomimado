# Reading with YomiMado

## Phase 1 toolbar (development source)

YomiMado now starts with a compact always-on-top toolbar. Drag its handle, or
focus the handle and use arrow keys, to move it. Collapse leaves Rescan and an
Expand control; the native window shrinks too. The overflow menu opens the
existing saved words/sentences, Settings (including detector import), sources
and Quit. Closing the secondary main window keeps the app running.

**Selected Area** scans a dragged region; **Whole Screen** scans the toolbar's
monitor without automatic page cropping. **Rescan** takes a new screenshot of
the last successful area/monitor; it is disabled until there is a successful scan.
Changed monitor layout/scaling requires a new scan selection. Hide/Show preserves
results without OCR; rescan if the underlying page changes. The toolbar shows
the active mode through its highlighted scan button. Scanning shows a spinner
and phase label inside that button; click it to cancel. The eye icon indicates
shown/hidden overlays, with no automatic status text row. A warning icon opens
error/model-setup details when needed; Escape dismisses those details. Compact
mode keeps both scan-mode icons, Rescan, visibility/status and expand on one row.
Screenshots still stay local.

`Cmd/Ctrl+Shift+O` selects an area on the monitor under the pointer.
`Cmd/Ctrl+Shift+S` now means Whole Screen on that monitor. This changes the older
page-scan shortcut described in the published v0.1.0 guide below. Toolbar buttons
use the toolbar's monitor; Rescan uses its recorded original monitor.

This source redesign is awaiting Phase 1 result approval. The learning popup,
legacy main-window controls and saved-data format remain unchanged. Full
settings/library/popup/overlay redesigns are deferred; published v0.1.0 installers
retain the following older interaction.

## Published v0.1.0 reading flow

Use the capture and learning flow below:

1. Press `Cmd+Shift+O` on macOS or `Ctrl+Shift+O` on Windows (or use **Select
   screen region** in the main window). For repeated manga scans, click
   **Scan manga page**. It tries a conservative automatic crop; if the page
   is uncertain, draw a reusable reading area once as the fallback.
2. For a selected-region capture, drag a rectangle on the current display.
3. The Rust capture layer returns an in-memory PNG crop and scaling metadata.
4. The app calls the local OCR service and shows its geometry in a transparent
   overlay. Without local models, the service shows a dashed **demo boundary**
   around the selected area. This is a coordinate check, not recognized text.
5. Click a recognized region to open a Japanese learning popup. Select a word
   in the popup's OCR text to see its reading, dictionary form, part of speech,
   and possible combined-word meanings from a local JMdict file. Click a kanji
   in that word for local KANJIDIC2 meanings and
   on/kun readings. The popup shows the selected word as its immediate usage
   context; it does not guess which character reading forms that word. After
   editing the text, press **Analyze words** to refresh
   word boundaries. Press **Translate locally** only if a sentence translation is
   wanted; translation never starts merely because OCR detected a region. In
   demo mode, enter Japanese text manually; the demo boundary contains no
   recognized text.
6. To keep a word, choose **Save this word** under its JMdict entry (or **Save
   without meaning** if no entry was found). Open **Saved words** in the main
   YomiMado window to review or remove it. Saving is explicit; OCR does not
   automatically add words to your history.
7. To keep the whole Japanese sentence, choose **Save sentence** in the popup.
   If you have already requested a local translation, saving also keeps that
   English result. Open **Saved sentences** in the main window to review or
   remove it. Saving a sentence does not start translation.

**Scan manga page** captures the current display, looks for a large
black-and-white manga page below darker browser controls, and sends only that
crop to OCR. If the page boundary is uncertain, it uses the saved manga area;
if there is none, it asks you to draw one. Use **Set/adjust scan area** if the
fallback area no longer matches the browser position. It is saved locally for
that display layout. Press `Cmd+Shift+S` on macOS or `Ctrl+Shift+S` on Windows
to start the same one-shot scan without opening the main window. Detection is
conservative: light-themed readers, dark or colored pages, and unusual layouts
may need the saved area. On dark sites, sparse white sidebar text and thumbnails
are excluded from the page crop when a distinct manga image is found; if two
page-like areas are similarly sized, the app uses the saved area instead. The
crop also excludes a short dark site toolbar beneath a clear light page edge.
Ambiguous dark page content is kept rather than cut off. The
app does not watch for screen changes or translate text automatically. Close
the overlay before changing pages, then scan again.
Reading-order controls are off by default. Enable **Reading-order controls** in
the main YomiMado window's Reading settings to show a fixed Previous/Next row
with the selected text below it on page scans; **Open** shows its learning
popup. There is no Reading order button on the manga overlay. The setting is
saved locally and applies to new scans.
This order uses text positions, not panel detection, so you can always click a
region directly if the suggested order is wrong.
Platform-specific coverage and remaining checks are recorded in the
[Windows installed-app record](windows-installed-test.md) and
[macOS installed-app record](macos-clean-mac-test.md).

See [development setup](development.md) for local models and dictionaries, or
the [release checklist](desktop-release.md) for packaged candidates.

### Development OCR region keyboard access (Phase 2)

With an OCR result visible, choose **More actions → Focus regions** on the floating
toolbar. Arrow keys move through detected regions; Home/End select the first/last.
Enter or Space opens the existing learning popup. Escape from a popup opened this
way returns to that region; Escape in region navigation hides the overlay and
retains its result. **Show OCR overlays** restores it without OCR. The optional
estimated manga reading-order setting remains separate from this keyboard navigation.

Normal outlines are orange; the selected region is blue. Dashed regions indicate
review, approximate geometry or an explicitly labeled demo boundary. Review guidance
also appears in the learning popup; use its existing OCR editor to correct text.
No word meaning or translation request runs merely because a region is hovered.

The native adapter is implemented for source review. Windows, mixed-DPI and rapid
pointer-entry acceptance remain tracked in [native UI checks](ui-overlay-testing.md).
These changes do not change the published v0.1.0 installers.
