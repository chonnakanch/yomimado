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
**Show OCR results**, **Saved**, **Settings**, **Sources & licenses** and
**Quit YomiMado**. On Windows,
left-click the notification-area icon to show and focus the toolbar; right-click
for the same menu. Windows may place the icon inside its notification-area
overflow; use Windows settings to keep it visible if desired.

Choose **Show OCR results** to restore the latest hidden outlines without
rescanning or bringing the toolbar forward. It is available only when a completed
result is hidden; it is disabled during scans, before the first result, after
clearing results and while outlines are already shown. If the page has changed,
use Rescan from the toolbar instead.

Choose **More actions → Hide Toolbar** or the tray menu's **Hide Toolbar** to hide
only the floating toolbar. Restore it from the icon. OCR overlays stay visible,
results stay available, and scan shortcuts keep working. The toolbar starts
visible again on the next launch. Tray window actions wait until any active scan
finishes or is canceled; Quit stays available. If the tray cannot start, the
toolbar stays available, its status control reports the error, and Hide Toolbar
is omitted. **Quit YomiMado** exits the app and stops its bundled OCR service.

### Customize capture shortcuts

Open **Settings → Scan & OCR → Scan shortcuts**, choose **Change** beside
Selected Area or Whole Screen, then press and release your preferred combination.
Changes save locally and apply immediately, including after restarting YomiMado.
Use Ctrl, Command/Windows or Alt/Option with a letter, number or F1–F24;
Shift is optional. Keys follow their physical keyboard position. Escape, Tab,
changing categories or leaving Settings cancels recording without saving.

The two actions must use different shortcuts. If a binding is unavailable or
cannot be saved, the previous binding remains active. Startup conflicts appear
as **Unavailable** in Settings; toolbar capture buttons remain usable.
**Restore defaults** restores both shortcuts together: `Cmd/Ctrl+Shift+O`
(Selected Area) and `Cmd/Ctrl+Shift+S` (Whole Screen). Some operating-system
shortcuts are reserved or consumed before the recorder can see them; choose a
different combination in that case.

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
After a scan completes, press **Escape** while reading to hide the OCR outlines,
or click the small **Hide OCR overlays** X button at the right of the overlay's
control strip. Results stay available through the toolbar's Show OCR overlays
toggle; showing them again does not rerun OCR. Escape in an open learning popup,
menu or Settings keeps its local behavior. If another app reserves Escape, use
the hide icon or toolbar toggle.

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

### Local backup and restore

Open **Saved → Backup & restore**. **Export backup** saves every saved word and
sentence to a JSON file through the native Save dialog, regardless of the current
tab or search filter. It includes Japanese text, readings, dictionary forms,
meanings, source sentences, saved translations, save dates and dictionary
attribution. Keep the file somewhere you can recover it when moving computers
or reinstalling YomiMado.

Choose **Restore backup**, select a YomiMado JSON backup and review the numbers
of new words, new sentences and duplicates. Nothing is imported until you choose
**Restore**. **Cancel** leaves your library unchanged.
Restore adds missing entries and skips duplicates, keeping existing meanings,
translations and dates. A word with the same spelling and reading but a different
source sentence is a separate entry. Reimporting the same file adds no duplicates.
Counts are checked again during restore if your library has changed since preview.

After restoring, the library refreshes and keeps your search. Errors stay visible
and can be retried; failed restore transactions add no entries. Unsupported,
invalid or oversized files are rejected. Backups support up to 16 MiB and 50,000
entries per collection. They contain saved text in plain JSON; screenshots,
models, settings and the translation cache are excluded. Backup and restore run
locally and do not request OCR, dictionary lookup or translation.

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

Click an OCR region to open its full Japanese sentence. **Words**, **Select** and
**Edit** switch how you work with the Japanese text. **Copy**, **Save** and
**Translate** are grouped below the sentence; word meanings and translation appear only
after explicit selection/request. Select a word in the sentence to see its
hiragana reading, base form, token-analysis POS and numbered possible meanings.
Alternative dictionary matches are collapsed; each has its own Save this word
action. Display readings use hiragana, while saved/lookup readings retain the
original dictionary data. Missing dictionaries still allow Save without meaning.

If a word boundary is wrong, choose **Select** above the sentence.
Drag over any continuous part of the Japanese sentence, or click to place the
visible cursor. Arrow keys move the cursor; Shift + arrow keys extend the
highlighted selection. The selection box blocks typing, deletion, paste, cut and
drop; use **Edit** to change the original sentence. Choose **Look up selection** to look
up that exact expression in local JMdict. Selection can cross automatic word
boundaries or include only part of a word, and works even if word analysis fails.
Leading/trailing whitespace is ignored; the lookup limit is 100 characters.
No match keeps the selection available to adjust and try again. Manual lookup
does not infer a base form or reading; dictionary matches show their own readings.
Saving a match keeps its expression as the dictionary form, its reading/meanings,
the selected surface and the original sentence. Kanji exploration still works.
Choose **Words**, or press Escape once, to return to automatic words;
Escape returns keyboard focus to **Words** before a later Escape closes
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
Use **Edit** to correct a known recognition error, or scan the area again.
This is a region review cue, not a character confidence score. The editor has no
confidence underlines because the OCR engine does not supply character confidence.

For an inflected verb or i-adjective, expand **Conjugation** in its word details.
The app includes adjacent analyzed endings and shows steps such as
食べました → 食べます → 食べる. Complete manual selections can also use their
analyzed base for local dictionary lookup. Common past/negative/polite forms,
ちゃう／じゃう contractions, ている／てる continuing-action/state forms and
たい desire forms are supported. For example, 読んでた expands through
読んでいた → 読んでいる → 読む; 食べたくなかった expands through
食べたくない → 食べたい → 食べる. The ている／てる family includes plain and
polite tense/negative forms; the たい family includes past/negative forms and
their polite です variants.

Explanations do not start translation or infer a context-specific meaning.
**Not covered** marks unsupported expressions, including passive/potential forms,
causatives and combined endings such as ていたい or てしまっている.

The sentence and its actions stay above scrollable details as the popup grows
to fit the available screen space. Long sentences have their own scroll area.

**Edit** opens a correction draft. **Reset to OCR text** restores the original
recognition text in the draft without applying it. **Apply** commits the draft and
refreshes word analysis and learning details. **Cancel** or Escape in the editor keeps
the applied sentence; Escape elsewhere closes the popup and returns keyboard
focus to the region when it was opened through region navigation. **Translate**
retains the existing explicit local translation/cache behavior. **Save**
includes a matching translation only when one has been requested. Copy/save
failures are shown inline and can be retried.

**Copy** briefly becomes **Copied** after a successful clipboard write. Saved
sentences and dictionary matches show **Saved** and prevent another save of the
same current result. Translation shows **Translating…** while running and **Retry**
after a failure. Its Local card can be collapsed or copied separately; translation
is not saved until you explicitly save the sentence. Requesting a translation
after saving enables Save again so you can retain the translation too.
