# Reading with YomiMado

## Quick start (current development source)

For a source checkout, first follow [development setup](development.md) to start
both the local service and desktop app. The minimal service returns a labeled
demo boundary until OCR models are configured. Packaged apps start their service
automatically; their exact features depend on the installed version.

1. Open your manga in its usual reader. On macOS, grant Screen Recording permission
   when requested and restart YomiMado.
2. Configure the detector in **More actions → Settings → Scan & OCR** for a
   packaged app, or configure the local OCR model paths for development.
3. Choose **Selected Area** and drag around text, or press `Cmd+Shift+O` on macOS /
   `Ctrl+Shift+O` on Windows. **Whole Screen** (`Cmd/Ctrl+Shift+S`) tries to find
   the page and asks for a fallback area when needed.
4. Click a detected region, then select a word or kanji in the learning popup.
   Dashed regions need review; use **Edit OCR text** to correct recognition.
   **Select text → Look up selection** lets you adjust a word boundary manually.
5. Use **Save this word** or **Save sentence** explicitly, then open **More
   actions → Saved** to review them. Translation is optional: configure a local
   provider in **Settings → Reading**, then choose **Translate locally**.
6. After changing pages, use **Rescan** if the reading area is unchanged, or run
   a new scan if the page moved. Choose **More actions → Quit YomiMado** when done.

Word and kanji meanings require local JMdict/KANJIDIC2 resources; the development
guide explains their setup. Reading, dictionary lookup and inference stay local.
The detailed controls below describe current source first, followed by the
historical v0.1.0 interface. For a code map, see [project structure](architecture.md#repository-map).

## Redesigned toolbar (development source)

YomiMado now starts with a compact always-on-top toolbar. Drag its handle, or
focus the handle and use arrow keys, to move it. Collapse retains both scan icons,
Rescan, overlay visibility/status and Expand; the native window shrinks too. The
overflow menu opens Saved, Settings (including detector import), Sources and Quit.
Closing the secondary main window keeps the app running.

### Tray / menu bar (development source)

The macOS menu bar icon opens a native menu with **Show Toolbar / Hide Toolbar**,
**Saved**, **Settings**, **Sources & licenses** and **Quit YomiMado**. On Windows,
left-click the notification-area icon to show and focus the toolbar; right-click
for the same menu. Windows may place the icon inside its notification-area
overflow; use Windows settings to keep it visible if desired.

Choose **More actions → Hide Toolbar** or the tray menu's **Hide Toolbar** to hide
only the floating toolbar. Restore it from the icon. OCR overlays stay visible,
results stay available, and scan shortcuts keep working. The toolbar starts
visible again on the next launch. Tray window actions wait until any active scan
finishes or is canceled; Quit stays available. If the tray cannot start, the
toolbar stays available, its status control reports the error, and Hide Toolbar
is omitted. **Quit YomiMado** exits the app and stops its bundled OCR service.

### Scanning

**Selected Area** scans exactly the region you drag. **Whole Screen** finds manga
pages on the toolbar's monitor and sends only the detected page/spread to local
OCR. On Windows, automatic detection excludes the monitor area reserved for the
taskbar, using the work area reported by Windows. If the page boundary is uncertain,
it uses the saved manga area for that display layout, or asks you to draw one.
It does not send the entire monitor to
OCR as an uncertainty fallback. **Rescan** takes new pixels from the last
successful area, including a detected crop; use Whole Screen again if the page
has moved. Rescan is disabled until there is a successful scan.
If selection is needed, a small bottom-edge hint says **Drag around pages · Esc cancel**.
Drag around a page or spread, including through the hint itself. It disappears
while you drag; Escape cancels selection.
Changed monitor layout/scaling requires a new scan selection. Hide/Show preserves
results without OCR; rescan if the underlying page changes. The toolbar shows
the active mode through its highlighted scan button. Scanning shows a spinner
and phase label inside that button; click it to cancel. The eye icon indicates
shown/hidden overlays, with no automatic status text row. A warning icon opens
error/model-setup details when needed; Escape dismisses those details. Compact
mode keeps both scan-mode icons, Rescan, visibility/status and expand on one row.
Both toolbar forms keep the same control height. Near the bottom of the work area,
More actions opens above the toolbar without moving its row. On short screens the
menu scrolls; Escape closes it and returns focus to More actions. More actions uses
a separate popover so showing or dismissing it does not resize the toolbar.
Screenshots still stay local.

Choose **More actions → Saved** to open the shared library. Use **Words** and
**Sentences** tabs to switch collections; Left/Right or Home/End moves between
tabs by keyboard. Each collection keeps its Refresh, loading/error/empty states
and confirmed Remove action. Opening the library or returning to a tab refreshes
that collection. Settings and Sources remain separate toolbar actions.

Search words by Japanese surface, base form, reading, meaning, or source sentence.
Search sentences by Japanese text or a saved English translation. Matching
ignores letter case, full/half width and hiragana/katakana differences. Multiple
terms must all match; no romaji conversion or translation is performed. Each tab
remembers its last query locally. Use **Clear search**, the search-field clear
button, or Escape to clear it. Refresh keeps the query and results retain their
stored newest-first order. Searching makes no lookup or translation request.

Words show larger Japanese headwords, their stored reading and numbered meanings.
Expand **Source sentence** for Japanese context, local save time and dictionary
attribution. Wider windows place headwords beside meanings; narrow windows stack
them. Sentences show the
Japanese and any English translation already saved; **Saved date** reveals their
local save time. Opening Saved never starts dictionary lookup or translation.

Rows wrap in narrow windows. A failed refresh keeps the previous rows and offers
Retry loading; a failed removal stays beside its row so you can try Remove again.
Removal still requires confirmation. During removal, other Remove/Refresh actions
are disabled. Keyboard focus returns to the next/previous row or Refresh when a
row is removed, and stays in the selected tab if you switched collections.

`Cmd/Ctrl+Shift+O` selects an area on the monitor under the pointer.
`Cmd/Ctrl+Shift+S` starts Whole Screen on that monitor, including automatic page
detection and saved/drawn-area fallback. Toolbar buttons use the toolbar's
monitor; Rescan uses its recorded original monitor.

Whole Screen can be the first scan after launch; Selected Area is not needed to
initialize it. Recognition allows up to three minutes for a cold local model or
large page. A stalled OCR request then ends with an error instead of leaving the
scan button busy indefinitely. Check the local OCR service before retrying.

The owner accepted the compact learning popup and Phase 4 Saved library, then
authorized Phase 5 Settings. Saved-data formats and native capture helpers are
retained. Saved, Settings, and Sources & licenses each open their own native
window from More actions. They can remain open together; opening another menu
entry does not replace an existing window's content. Published v0.1.0 installers
retain the older interaction below.

### Settings (Phase 5 development source)

Choose **More actions → Settings** for **Scan & OCR**. It contains detector status
and Refresh status, checksum-verified Select/Replace detector model, capture
permission guidance and scan shortcuts. Canceling the file picker keeps the model;
a failed import shows an error and leaves the installed model intact. Restart
YomiMado after replacing a model already in use. In development, model setup is
managed by the existing local OCR service; the app does not claim that service is
ready based on the packaged model status.

**Reading** explains **More actions → Read with keyboard**, which replaces the
old Reading-order controls preference and Previous/Next text panel. No preference
needs to be enabled before using keyboard reading.
Under **Local translation → Model source**, choose **Import local model** for
compatible Marian folders or **Ollama** for installed local text models or
explicit downloads by model name. A fresh setup shows **No translation model
installed**. Choose **Import and use model** or **Use this model** to activate your
choice; the **Using** line confirms it. There is no built-in model option or
automatic fallback. OCR and word/kanji lookup work without a translation model.
After installation, choose **Translate locally** in a learning popup; no restart
is needed. Opening settings or scanning never starts a model download.
Ollama must be installed and running separately. See
[model selection and supported formats](translation-model-selection.md).
**More actions → Sources & licenses** opens a separate attribution window with
dictionary/model links and packaged notice guidance.
Use Left/Right or Home/End on category tabs to navigate by keyboard.

Use the native window close button to hide this window. The native title bar
also provides window movement, minimizing and resizing.
Closing a window leaves the other windows, toolbar and reading session running. Reopen it
through the toolbar; **More actions → Quit YomiMado** exits the app. Scan actions
remain on the toolbar. Whole Screen includes automatic manga-page cropping;
the historical installer instructions below still apply to v0.1.0.

If a macOS utility such as Vorssaint quits apps when their last window closes,
add YomiMado to that utility's exceptions. Its bundle identifier is
`com.yomimado.desktop`. A bare command-launched development executable may have
no macOS bundle identifier, so a bundle-based exception may not cover it.

### Compact learning popup (Phase 3 development source)

Click an OCR region to open its full Japanese sentence. Copy sentence and Save
sentence are available immediately; word meanings and translation appear only
after explicit selection/request. Select a word in the sentence to see its
hiragana reading, base form, token-analysis POS and numbered possible meanings.
Alternative dictionary matches are collapsed; each has its own Save this word
action. Display readings use hiragana, while saved/lookup readings retain the
original dictionary data. Missing dictionaries still allow Save without meaning.

If a word boundary is wrong, choose **Select text** above the learning details.
Drag over any continuous part of the Japanese sentence, or click to place the
visible cursor. Arrow keys move the cursor; Shift + arrow keys extend the
highlighted selection. The selection box blocks typing, deletion, paste, cut and
drop; use **Edit OCR text** to change the original sentence. Choose **Look up selection** to look
up that exact expression in local JMdict. Selection can cross automatic word
boundaries or include only part of a word, and works even if word analysis fails.
Leading/trailing whitespace is ignored; the lookup limit is 100 characters.
No match keeps the selection available to adjust and try again. Manual lookup
does not infer a base form or reading; dictionary matches show their own readings.
Saving a match keeps its expression as the dictionary form, its reading/meanings,
the selected surface and the original sentence. Kanji exploration still works.
Choose **Back to normal**, or press Escape once, to return to automatic words;
Escape returns keyboard focus to **Select text** before a later Escape closes
the popup. Selecting or looking up text never changes OCR text or starts translation.

Select a kanji below the word for meanings and on’yomi/kun’yomi. Expand Example
compounds to load short local JMdict words; this does not require translation.

Word matches and Saved words can show a small **N5–N1** badge. These are estimated
JLPT vocabulary levels from a bundled community dataset, matched by dictionary
spelling and reading. Unlisted words and missing readings receive no badge;
an absent badge does not mean N1 or "beyond JLPT." Existing saved words use their
stored dictionary form and reading. The badge does not rate an entire sentence
or assign a separate level to its individual kanji.

Use **Settings → Reading → Show estimated JLPT levels** to hide or restore badges.
The choice is saved locally and updates open learning/library windows. Tags work
offline and require no extra setup, model, API key or lookup service. See
**Sources & licenses** for attribution and the full data license.

**Check OCR** marks uncertain or approximate text for review against the page.
Use **Edit OCR text** to correct a known recognition error, or scan the area again.

For an inflected verb or i-adjective, expand **Conjugation** in its word details.
The app includes adjacent analyzed endings and shows steps such as
食べました → 食べます → 食べる. Complete manual selections can also use their
analyzed base for local dictionary lookup. Common past/negative/polite forms and
ちゃう／じゃう contractions are supported; **Not covered** marks unsupported
forms. Explanations do not start translation or infer a context-specific meaning.
See the [supported forms and limits](implementation-plan.md#conjugation-behavior-and-supported-forms).

The sentence and its actions stay above scrollable details as the popup grows
to its work-area limit. Long sentences have their own scroll area.

Edit OCR text opens a correction draft. Apply and analyze commits it, resets
dependent learning results and retokenizes. Cancel or Escape in the editor keeps
the applied sentence; Escape elsewhere closes the popup and returns keyboard
focus to the region when it was opened through region navigation. Translate
locally retains the existing explicit translation/cache behavior. Save sentence
includes a matching translation only when one has been requested. Copy/save
failures are shown inline and can be retried.

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
After scanning, choose **More actions → Read with keyboard**. The OCR overlays
must be visible and the scan finished. Arrow keys select the next/previous region;
Home/End select the first/last region. Enter or Space opens its learning popup.
Escape closes the popup and returns focus to that region. Escape from region
navigation hides the overlays and returns to the toolbar. Show the overlays again
to resume. No translation runs merely because selection changes.
Navigation follows the detected sequence; estimated order on whole-screen scans
uses text positions, not panel detection. Click any region directly if it is wrong.
Platform-specific coverage and remaining checks are recorded in the
[Windows installed-app record](windows-installed-test.md) and
[macOS installed-app record](macos-clean-mac-test.md).

See [development setup](development.md) for local models and dictionaries, or
the [release checklist](desktop-release.md) for packaged candidates.

### Development OCR overlays

Click a detected region to open its learning popup. **Show OCR overlays** restores
a hidden result without OCR. Use **More actions → Read with keyboard** to focus
regions without opening a popup. Ordinary scan completion keeps focus in your reader.

Normal outlines are orange; the selected region is blue. Dashed regions indicate
review, approximate geometry or an explicitly labeled demo boundary. Review guidance
also appears in the learning popup; use its existing OCR editor to correct text.
No word meaning or translation request runs merely because a region is hovered.

Detailed hover tooltips are reserved for capture debug mode (`VITE_CAPTURE_DEBUG=1`).
Normal reading retains screen-reader labels, dashed review cues and the compact
Check OCR status. Debug mode pauses before the interactive overlay so you can
review the exact capture and recognized text; expand Geometry or Detector stage
for diagnostic details. See [development setup](development.md) to enable it.

The native adapter is implemented for source review. Windows, mixed-DPI and rapid
pointer-entry acceptance remain tracked in [native UI checks](ui-testing.md#native-overlay-checks).
These changes do not change the published v0.1.0 installers.
