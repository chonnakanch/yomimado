# Reading with YomiMado

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
