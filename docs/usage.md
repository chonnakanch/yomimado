# Reading with YomiMado

Start with the [installation guide](installation-guide.md) to install the app,
configure the detector and make your first scan. This guide explains the reading
controls after setup.

## Reading controls

YomiMado starts with a compact always-on-top toolbar. Drag its handle, or
focus the handle and use arrow keys, to move it. Collapse retains both scan icons,
Rescan, overlay visibility/status and Expand. The overflow menu opens Saved,
Settings, Sources & licenses and Quit. Closing Saved or Settings keeps the app
running.

### Tray / menu bar

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
and phase label inside that button; click it to cancel. The eye icon shows whether
overlays are visible. A warning icon opens
error/model-setup details when needed; Escape dismisses those details. Compact
mode keeps both scan-mode icons, Rescan, visibility/status and expand on one row.
Both toolbar forms keep the same control height. Near the bottom of the work area,
More actions opens above the toolbar without moving its row. On short screens the
menu scrolls; Escape closes it and returns focus to More actions.
Screenshots still stay local.

`Cmd/Ctrl+Shift+O` selects an area on the monitor under the pointer.
`Cmd/Ctrl+Shift+S` starts Whole Screen on that monitor, including automatic page
detection and saved/drawn-area fallback. Toolbar buttons use the toolbar's
monitor; Rescan uses its recorded original monitor.

Whole Screen can be the first scan after launch; Selected Area is not needed to
initialize it. Recognition allows up to three minutes for a cold local model or
large page. A stalled OCR request then ends with an error instead of leaving the
scan button busy indefinitely. If an error persists, quit and reopen YomiMado
before retrying.

Saved, Settings and Sources & licenses each open their own native window from
More actions. They can remain open together; opening another menu entry does
not replace an existing window's content.

### Saved words and sentences

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

### Keyboard reading

After a scan finishes, choose **More actions → Read with keyboard** while the
OCR overlays are visible. Arrows select the next/previous region; Home/End select
the first/last. Enter or Space opens its learning popup. Escape closes the popup
and returns focus to its region. Escape from region navigation hides overlays
and returns to the toolbar; Show restores them without another scan.

Selection never starts translation. Navigation follows the detected sequence;
estimated order uses text positions rather than panel detection. Click any region
directly when that order is wrong.

### Settings

Choose **More actions → Settings** to open **Scan & OCR** or **Reading**.
Scan & OCR shows detector status, capture permission guidance and shortcuts.
Reading contains keyboard-reading help, estimated JLPT badge visibility and local
translation choices. Use Left/Right or Home/End on category tabs to navigate.

For detector installation and translation setup, follow the
[installation guide](installation-guide.md). For compatible model files and provider
switching, see [translation model setup](translation-model-selection.md).
**More actions → Sources & licenses** opens attribution in a separate window.

Use the native window close button to hide this window. The native title bar
also provides window movement, minimizing and resizing.
Closing a window leaves the other windows, toolbar and reading session running. Reopen it
through the toolbar; **More actions → Quit YomiMado** exits the app. Scan actions
remain on the toolbar. Whole Screen includes automatic manga-page cropping.

If a macOS utility such as Vorssaint quits apps when their last window closes,
add YomiMado to that utility's exceptions. Its bundle identifier is
`com.yomimado.desktop`.

### Learning popup

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
Passive/potential forms, causatives, progressive forms and other unsupported
expressions remain **Not covered**.

The sentence and its actions stay above scrollable details as the popup grows
to fit the available screen space. Long sentences have their own scroll area.

Edit OCR text opens a correction draft. **Apply and analyze** applies it and
refreshes word analysis and learning details. Cancel or Escape in the editor keeps
the applied sentence; Escape elsewhere closes the popup and returns keyboard
focus to the region when it was opened through region navigation. Translate
locally retains the existing explicit translation/cache behavior. Save sentence
includes a matching translation only when one has been requested. Copy/save
failures are shown inline and can be retried.
