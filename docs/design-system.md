# YomiMado design system

This guide defines visual tokens, component behavior, tray contracts and icon
provenance. Use [architecture](architecture.md) for runtime boundaries,
[implementation status](implementation-plan.md) for priorities, and
[UI testing](ui-testing.md) for review evidence and native acceptance.

## 1. Visual direction and boundaries

Use the supplied local images in `docs/design-references/` for compact utility
window composition, Japanese sentence/word hierarchy and restrained dark
surfaces. Use the written palette and feature list as the source of truth.
The detailed popup image's disclosure rhythm is useful; audio, full conjugation
tables, example sentences and related-word features remain future scope. The
implemented limited conjugation disclosure is documented in the feature plan.

Keep the original manga visible. Opaque surfaces belong to the toolbar, popup
and secondary window. The default OCR layer remains transparent except for
outlines and very light hover/selection fill. The opt-in **Translate bubbles automatically**
setting temporarily covers detected text bounds with white translation panels;
turning it off reveals the Japanese. Do not modify the manga image or add a
full-screen dimmer, loud status banner or decorative motion in the reading view.

Jisho-inspired means a readable headword, reading, base form, POS and numbered
definitions. It does not mean copying Jisho assets or implying the existing
service exposes every Jisho field.

## 2. Semantic color tokens

Declare tokens centrally in `apps/desktop/src/styles/tokens.css`; component
styles consume roles, never repeat hex values. The table matches the shared token definitions.

| CSS token                                          | Value                       | Role                                                  |
| -------------------------------------------------- | --------------------------- | ----------------------------------------------------- |
| `--color-background`                               | `#131519`                   | Secondary-window canvas.                              |
| `--color-surface`                                  | `#1A1D24`                   | Toolbar, cards and inputs.                            |
| `--color-surface-elevated`                         | `var(--color-surface)`      | Quiet control surfaces.                               |
| `--color-menu-surface / --color-popup-surface`     | `#20242C`                   | Raised menu and learning-popup surfaces.              |
| `--color-accent`                                   | `#0080FF`                   | Primary actions, active controls and OCR outlines.    |
| `--color-accent-hover / --color-link`              | `#339AFF`                   | Hover actions and small link text.                    |
| `--color-accent-pressed`                           | `#0066CC`                   | Pressed primary actions.                              |
| `--color-accent-tint`                              | `rgb(0 128 255 / 0.16)`     | Selected Settings/mode tabs and menu hover.           |
| `--color-brand`                                    | `#D98B5F`                   | Logo frame, toolbar book and saved bookmark identity. |
| `--color-selected`                                 | `var(--color-accent)`       | Chosen token or character.                            |
| `--color-text-primary`                             | `#F2F4F8`                   | Japanese and primary UI text.                         |
| `--color-text-secondary / --color-text-muted`      | `#8B93A3`                   | Readings, metadata and supporting text.               |
| `--color-border`                                   | `#3A4150`                   | Surface borders and dividers.                         |
| `--color-success / --color-success-tint`           | `#2DD4A0 / 14% tint`        | Successful-action feedback and saved-word highlights.  |
| `--color-on-accent`                                | `#FFFFFF`                   | Text/icon on filled blue actions and selections.      |
| `--color-focus`                                    | `var(--color-accent)`       | Keyboard focus outline.                               |
| `--color-status-error / --color-error-tint`        | `#FF5C5C / 14% tint`        | Error and destructive feedback.                       |
| `--color-warning / --color-warning-tint`           | `#F4B544 / 14% tint`        | OCR review cue.                                       |
| `--color-region-default / --color-region-selected` | `var(--color-accent)`       | Ordinary and selected OCR strokes.                    |
| `--color-region-hover`                             | `var(--color-accent-hover)` | Hovered OCR strokes.                                  |
| `--color-region-fill`                              | `rgb(0 128 255 / 0.14)`     | OCR interior, including hover and selection.          |
| `--color-capture-edge`                             | `var(--color-background)`   | Thin dark edge on capture selection only.             |
| `--color-capture-selection`                        | `var(--color-accent)`       | Capture drag rectangle border.                        |
| `--color-capture-selection-fill`                   | `var(--color-region-fill)`  | Fill inside the dragged rectangle.                    |
| `--color-debug-candidate`                          | `#58D5E8`                   | Detector candidates in the debug preview only.        |

Blue identifies clickable/active controls; copper is reserved for identity marks,
never filled buttons. Use white labels on primary actions, readable blue links
and explicit success/error labels. Verify contrast against actual composited
styles; historical measurements in the UI testing guide apply only to their
stated palette. Keep keyboard focus visible independently of hover.

Do not dim entire components with parent opacity when that makes their text
unreadable. Disabled actions retain legible labels, suppress hover behavior and
show why they are unavailable (for example, no scan yet or missing model).
Errors use inline messages and retry; success uses a short “Saved locally” or
“Installed” label without moving nearby controls.

## 3. Typography

| Role                            | Size / line height           | Weight and treatment                             |
| ------------------------------- | ---------------------------- | ------------------------------------------------ |
| Selected vocabulary             | 30 px / 1.35 (allowed 28–32) | 600; Japanese font stack; wrap long words.       |
| Japanese sentence               | 20 px / 1.75 (allowed 18–20) | 400; preserve source punctuation and whitespace. |
| Selected-word reading           | 16 px / 1.5                  | 400; hiragana display where conversion is known. |
| Kanji character                 | 32 px / 1.35                 | 500; never imply the glyph's stroke count.       |
| Definitions and collection body | 15 px / 1.55 (allowed 14–16) | 400; numbered senses, natural wrapping.          |
| Action labels                   | 13 px / 1.4                  | 500–600; avoid all caps and excessive bold.      |
| Labels, POS and metadata        | 12–13 px / 1.5               | 400–500; secondary text, not tiny badges.        |
| Section heading                 | 14 px / 1.4                  | 600; short names, restrained contrast.           |

Font stacks:

```css
--font-ui:
  "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
--font-japanese:
  "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Hiragino Sans", "Yu Gothic UI",
  "Yu Gothic", "Meiryo", sans-serif;
```

Apply `lang="ja"` and the Japanese stack to sentence, surface, reading and kanji;
UI/English text uses the UI stack. Use tabular numerals for counts if available.
Do not letter-space Japanese, shrink it to fit a row, or make romanization a
second reading line. Reading presentation must not mutate lookup/save payloads.

The named fonts are preferred when installed; native fallbacks must work fully offline on both
targets. If consistent Noto Sans JP/Inter bundling is later selected, pin the
exact assets and verify their individual license/notice and package-size impact
before adding them. Do not silently depend on a Google Fonts request.

## 4. Spacing, sizing and shape

Use logical CSS pixels and a 4 px spacing system. Rust converts native window
dimensions using the actual display scale; do not multiply CSS values by DPI.

| Token                 | Value            | Typical use                                    |
| --------------------- | ---------------- | ---------------------------------------------- |
| `--space-1`           | 4 px             | Label/icon and small inline gaps.              |
| `--space-2`           | 8 px             | Related actions and tight row gaps.            |
| `--space-3`           | 12 px            | Component padding and related detail spacing.  |
| `--space-4`           | 16 px            | Popup/secondary panel padding.                 |
| `--space-6`           | 24 px            | Section separation.                            |
| `--space-8`           | 32 px            | Large secondary-window grouping only.          |
| `--radius-small`      | 4 px             | Token and character focus surfaces.            |
| `--radius-control`    | 8 px             | Buttons, inputs and rows.                      |
| `--radius-window`     | 12 px            | Toolbar window surface.                        |
| `--radius-card`       | 14 px            | Cards, popup and overflow menu.                |
| `--control-compact`   | 32 px            | Small menu and token-adjacent actions.         |
| `--control-default`   | 36 px            | Toolbar/settings action height.                |
| `--popup-width`       | 420 px           | Preferred logical width; work-area clamp wins. |
| `--popup-padding`     | `var(--space-4)` | Single outer padding.                          |
| `--popup-section-gap` | `var(--space-6)` | Distinct content sections.                     |
| `--focus-width`       | 3 px             | Visible focus outline, 2 px offset.            |
| `--motion-fast`       | 120 ms           | Color/fill feedback only.                      |

Toolbar starts around 536 × 56 logical px, compact around 244 × 56. Compact mode retains both scan icons, Rescan,
overlay visibility/status and expand on one row. These are
layout targets, not fixed minimums that can clip labels. Popups grow naturally
until their work-area cap (roughly 70% height), then scroll the details. At narrow
widths stack reading/metadata below the word, wrap footer actions and retain
Japanese type size. Clamp native positions to actual work area with a 12 logical
px screen inset and 8 logical px anchor gap, reusing tested placement behavior.
On launch, center the toolbar near the bottom of the primary display's work area,
above the Dock/taskbar with the same 12 logical px inset. Place the native window
before showing it, and center the first measured compact/expanded row once.
Later resizing preserves the user's dragged position.

Both toolbar forms retain a 56 px row and 36 px controls; collapsing changes width
and labels rather than control height. Overflow uses its own small native popover,
positioned below when space permits or above otherwise; opening/dismissing it never
resizes the toolbar. Status details retain their on-demand inline panel. Bound and
scroll panels on short work areas.

The native overflow popover starts without a focus ring after mouse opening.
Keyboard navigation shows the blue 2 px ring inset inside its menu row, so it
cannot collide with adjacent rows or the window edge.

Cards use a surface fill, 1 px border and 14 px radius without shadows. Do not
add native overlay shadows that shift geometry. Surface borders are 1 px;
focus and selected outlines are distinct from those decorative borders.
Suppress transitions under `prefers-reduced-motion`. No window-position animation,
scale animation or repeated pulsing while OCR is running.

## 5. Component specifications

### FloatingToolbar and ScanModeButton

One restrained surface; separate drag handle from buttons. Use short text for
Selected Area and Whole Screen, with a simple 16–20 px icon where useful.
Use copper for the book identity mark and blue for the primary scan action.
Controls use 3 px keyboard focus rings. Active Settings tabs have a blue border
and 16% blue fill; Saved tabs use a 2 px blue underline. Settings begins with its
heading, without a repeated app-name header. The overflow menu uses white labels,
muted disabled items, rounded 16% blue hover rows and a divider before Hide/Quit.
Rescan and Hide/Show may use icons with accessible names. Hover tooltips appear
only with capture debug mode enabled (`VITE_CAPTURE_DEBUG=1`).
Do not infer meaning from an icon alone. The model-install action belongs in
Scan & OCR; missing models/errors use a warning icon with details and a setup
link shown only when requested.

Whole Screen searches its target monitor for manga pages and crops the detected
page/spread before OCR. An uncertain boundary uses a saved/drawn manga area;
Selected Area scans the exact manual rectangle. Explain this in the debug scan tooltip
and Scan & OCR help. Rescan reuses the last successful crop/area.

An uncertain manga boundary uses the **Edge hint**: a compact bottom-centred
pill reading “Drag around pages · Esc cancel,” approximately 30 logical px high.
Selected Area uses the same hint with “Drag to capture · Esc cancel.”
It and any error detail ignore pointer events, so a drag can begin through the hint.
Hide the hint immediately while dragging; Escape cancels. Keep longer explanations
in help rather than over the reading area. Expected uncertainty is not an error;
actual capture/save failures retain an accessible alert above the hint.
Draw the capture rectangle with a 2 CSS px `#0080FF` border, a thin dark inner
and outer edge, and a 14% blue fill inside the rectangle. Keep the rest of the
selector fully transparent; do not apply a full-screen tint. Hide all selection
chrome before capture using the existing capture state.
Only a primary-button drag starts a selection. Suppress the selector's context
menu; secondary-button chords, context clicks and lost pointer capture reset the
current drag so another selection can start without closing the selector.
Disable the browser right-click context menu in every app window, including
Settings, Saved, the toolbar, learning popups and OCR overlays.

Mark overlay visibility with an accessible pressed state and current label.
The current scan or retained result determines which scan button is pressed and
accented. Keep collapse/expand operable by keyboard. Busy status (“Capturing…”,
“Recognizing…”) and an indeterminate spinner appear inside that scan button;
clicking it cancels its exact active session. Routine status has no visible text
row, but remains a polite live region; errors are alerts with optional details.
Stop spinner motion with reduced motion. Avoid fake percentages
because existing OCR APIs do not expose progress. Overflow is anchored to the
toolbar, clamped to work area, supports keyboard dismissal and excludes the drag
region. Quit remains discoverable after expanding the toolbar.

### OCRBoundingBox

| State              | Stroke                 | Fill            | Additional cue                                              |
| ------------------ | ---------------------- | --------------- | ----------------------------------------------------------- |
| Default            | 2 CSS px blue          | Blue at 14%     | Region orientation in accessible label.                     |
| Hover              | 2 CSS px brighter blue | Blue at 14%     | Pointer cursor, no lookup triggered.                        |
| Selected           | 2 CSS px blue          | Blue at 14%     | Selected semantics and keyboard focus if active.            |
| Review/approximate | Same state colors      | Same state fill | Dashed stroke and “Review OCR” / “Approximate region” text. |
| Demo               | Dashed outline         | Transparent     | “Demo boundary — no recognized text.”                       |

Render one original polygon per region with a bright blue stroke and no black
border, halo or drop shadow. Default and selected strokes use `#0080FF`; hover
uses `#339AFF`. All ordinary states retain a 14% blue fill.
Use `vector-effect: non-scaling-stroke`. Keep original polygons; the component
name does not justify reducing geometry to a rectangle. Region fill/hit area
can remain clickable while visually transparent. Label uncertainty explicitly;
unknown confidence must never become a percentage badge. Apply selected color
after hover styling so hovering a selected region does not erase selection.

Use **More actions → Read with keyboard** as the explicit keyboard entry for visible
OCR results. Arrows select regions, Home/End jump to the first/last, and Enter/Space
opens the selected popup. Escape returns from the popup to its region; Escape in
the region navigator hides overlays and focuses the toolbar. Keep keyboard entry
out of scan completion so focus stays in the reader. A temporary native Escape
shortcut hides completed visible overlays from the reader without focusing the
app. Release it during scans, while results are hidden and when another YomiMado
window owns input; popup/menu/Settings Escape retains its local behavior.

Add a 28 px close button at the right of the overlay's existing 32 px control
strip, with a bold 20 px X, bright border and high-contrast foreground on a dark
surface. Use the accessible label **Hide OCR overlays** and an Esc tooltip. Keep
it inside the measured viewport, including full-screen captures with no outer
gutter. Report only its measured hit rectangle through the existing native
control route; the surrounding manga stays transparent and click-through.
Hiding retains results and Rescan state; the toolbar visibility toggle restores
the result. Late hide requests must not dismiss a newer result or active scan.

Place **Translate bubbles automatically** in **Settings → Reading → Bubble
translation**, above model selection. It is off by default and persists across
scans, restored results and app restarts. Report a failed preference write without
changing the checkbox's state. Remove the translation toggle from the overlay;
show only temporary progress or an error with Retry when automatic translation
is enabled. Remove the status group after completion. Translated text and its
underlying polygon must not show hover tooltips. Disabling the setting reveals
Japanese and stops queued work. Hiding an overlay stops that run without disabling the setting.
Preserve original polygons, dashed review outlines and region keyboard navigation.
Report the measured status group and each translated panel through the native
route as well as the hide button.

Translation panels use white with near-black text for reading against light/dark
pages. Panels grow only as needed within the capture and shared gaps to
neighboring text, up to 240 × 220 CSS px unless the original region is larger.
Add a labeled **Translation font size** select and live text preview in the
Bubble translation card. Default to **Automatic (fit text)**, using available
width and height at 18 px before reducing to 11 px. Fixed choices are 12, 14, 16,
18, 20, 24, 28 and 32 px: grow panels as needed, keep the selected size and allow
overflow scrolling instead of shrinking it. Persist the choice and update visible
panels across windows without new translation requests. Invalid/unavailable
storage falls back to Automatic; failed writes preserve the selection and report
an error.
Wrap English at spaces, collapse source line breaks into spaces, and disable
automatic hyphenation and forced word splitting. If the full text still cannot fit, keep its first line
visible and allow vertical scrolling; never hide it behind an ellipsis. Panels
accept scrolling and clicks, while retaining dashed review/selected borders.
Clicking opens the full translation and Japanese in the learning popup. Known
sound effects remain untouched. No persistent manga
replacement, automatic saving or assumed bubble segmentation is introduced.

Native hit routing is covered by the [overlay checks](ui-testing.md#native-overlay-checks).
`pointer-events` only selects DOM targets; visual transparency alone is not proof
that underlying applications receive input.

### DictionaryPopup and ClickableSentence

The first view contains the Japanese sentence, Copy/Save/Translate actions,
close control, and a quiet word-selection instruction. No headword, meanings,
kanji or translation result before explicit selection/request. Show the source
while tokenization loads or fails. The reference image's full-sentence hierarchy
applies; its always-visible English translation does not.

Keep sentence and sentence actions visible above the scrollable details. If
the sentence itself is very long, cap its own area with accessible scrolling.
Token controls read as continuous Japanese, with minimal inline padding and no
large chip gaps. Preserve literal text segments between tokens. Use native
buttons or equivalent keyboard semantics with visible focus and selected state;
do not nest character buttons within token buttons. A selected token receives a
blue cue; normal hover uses a quiet accent cue. Keep ordinary text selection and
explicit sentence copying usable.

Saved dictionary spellings use `--color-success-tint` with a
`--color-success` underline in Words mode. Keep primary Japanese text unchanged;
hover and selected blue cues take precedence. Include “saved word” in the
accessible token name, without adding icons, badges or status buttons to the
sentence. Select/Edit retain their original text controls. Saved membership is
the only vocabulary marker; there are no separate known/learning states.

Use a three-part **Words / Select / Edit** mode bar. Words retains the original
token split; Select uses native caret/range selection without modifying the
source. Both share a bordered sentence card and Copy/Save/Translate actions.
Pin actions beneath the text area. Keep visible selection help to one short
sentence; retain full caret/keyboard guidance in its accessible description.
Mode tabs support arrows/Home/End for focus and Enter/Space for activation.

Edit replaces the visible sentence card with a labeled Japanese textarea and
Reset to OCR text, Cancel and Apply controls. A reset changes only the draft;
Cancel/Escape returns to Words without changing applied data. Apply resets dependent
lookup/translation/save states and analyzes the correction. Disable spellcheck;
do not draw character confidence underlines or infer them from unknown confidence.
Inset the Edit textarea focus ring so scroll containers cannot clip its edges.
Review/approximate regions show a small
outlined status icon and **Check OCR** beside the Japanese heading, without a
warning block or repeated edit action. Keep the full review reason and correction
guidance in its debug-only hover tooltip and screen-reader text. Use an 11 px caption token,
12 px icon and 2 px icon/text gap for this brief status, preserving its contrast.
Demo text is identified and never treated as recognized Japanese.

Show source Copy feedback as green **Copied** for 1.5 seconds. Sentence and word
save actions show **Saved**, retain a copper bookmark identity mark and disable
duplicate saves for that current result. Primary word saving sits beside the
selected headword; alternative matches retain entry-specific saves. Translation
uses **Translating…**/busy and **Retry**/error states. Keep the requested Local
translation card above dictionary details, with separate copy and collapse controls
and explicit unsaved/saved-with-sentence text. No translation or saving happens
on mode changes, word selection or card expansion. Conjugation summaries and
Example compounds use blue labels without a filled hover/pressed background.
Conjugation is present only when the selected analyzed form needs an explanation.
Keep shared potential/passive/honorific interpretations together in that existing
disclosure, with a short context note; do not add meaning-choice controls or pick
one meaning from the suffix alone. Long summaries wrap within the details column.

### CaptureDebugPreview

Use the same surface, border, spacing, Japanese typography and 36 px utility
buttons as the app. Keep the exact in-memory capture fitted without
stretching; show readable recognized text alongside it, stacking the panes at
narrow widths. Each pane scrolls independently and has visible keyboard focus.
Keep Show overlay disabled while recognition is pending and Close available.
Errors retain the capture and use an accessible alert.

Use the normal blue for final regions and dashed blue for review/approximate
geometry. Detector candidates use the dedicated cyan token with a thinner dashed
stroke; filtered candidates use muted dotted strokes. Pair the colors with a
compact labeled legend. Preserve all source geometry, retry/crop information and
unknown-confidence labels. Collapse Geometry and Detector stage details by default.

The existing capture debug flag controls this preview and hover tooltips on the
toolbar, OCR polygons and popup review indicator. Normal reading keeps accessible
names, review metadata and the small Check OCR indicator without hover popups.
No debug setting is added to production Settings.

### WordDefinition and AlternativeDictionaryMatches

Order: selected surface, hiragana reading, base form, morphological POS,
numbered English senses, entry-specific Save word, attribution. Base form can be
an inline labeled field, even when equal to surface; no fabricated inflection
table. Token POS is supplied by Lindera/IPADIC, separately from dictionary-sense POS. Do not generate
English glosses when the API has none.

Use the existing ranked first entry as the initial possible match after selection;
show its match/mismatch cues. Put additional results in a collapsed disclosure
with count. Expanded entries get their own reading, senses and save button;
maintain service order and identify which match will be saved. Do not present a
ranked match as a guaranteed contextual meaning. Empty/error states preserve
selected-word metadata and the existing Save without meaning option.

### KanjiDetail and ExampleCompounds

Show character buttons for Han characters in the selected word with useful
accessible names. Selection reveals a prominent character, English meanings,
on'yomi and kun'yomi with clear labels. Use the selected word for context without
repeating the full source sentence underneath it. Do not split word readings
into guessed per-kanji readings. Keep on'yomi/kun'yomi conventions unchanged.

Compounds sit in a collapsed disclosure and load on expansion. Rows contain
expression, reading and short English meanings supplied by the API. Loading,
missing data and failed compound lookup are independent of kanji-detail success.
No sentence corpus, audio, stroke count, JLPT, WaniKani or Wikipedia section.

### SaveWordButton, SaveSentenceButton and translation

Save is always explicit. States: idle → saving → saved, or inline error/retry.
Prevent accidental duplicate clicks while saving. Switching entry/word/sentence
invalidates feedback for the previous selection; retain the existing backend
upsert rules. The success color accompanies text, not a color-only icon.

Copy confirms “Copied” after success and reports failure without claiming success.
Save sentence is available before translation; a matching requested translation
can be retained with it. A secondary Translate locally control reveals the
existing English output only after a request. Cache reuse stays internal. Both
the Japanese and English remain accessible; changing source clears stale output.

Align the translation card with the Japanese sentence card. Center the title
and Local badge together; keep Copy and collapse controls grouped at
the right, allowing metadata to wrap at narrow widths. Show the sentence's save
status below the result without a “Machine translation” label.

### Saved collections and SettingsWindow

Toolbar navigation has separate **Saved**, **Settings**, and **Sources & licenses**
windows. There is no Saved/Settings navigation inside those windows. Saved keeps
**Words** and **Sentences** tabs inside its library. Use
dictionary-style rows with prominent Japanese headwords, readings, numbered
senses and expandable context. Use underlined Words/Sentences tabs and a search
field; stack headwords and meanings at narrow widths. Keep local dates, existing stored order,
refresh/error/empty states and confirmed Remove actions. Lists remain readable
with larger text and narrow windows.

Keep **Backup & restore** as a collapsed disclosure above the collection search.
Use one short helper sentence, a compact count preview and **Restore / Cancel**
controls. Keep format/resource details in the reading guide and attribution in
backup files and existing Sources/entry views.
Use native file dialogs and explicit Export/Restore labels. Restore first shows
the selected file name and new/duplicate counts, explaining that existing entries
stay unchanged. Focus its confirmation button (or the preview when nothing is new)
and return focus to Restore backup after cancel/success. Announce progress/results
and show retryable errors inline. Keep both action rows wrapping at narrow widths,
and refresh collections after restore without clearing searches.

Settings uses ordinary labeled controls for actual capabilities. Scan & OCR holds
verified detector status/import/replacement and editable capture shortcuts;
show a readable chord and labeled Change button for each capture action. Recording
has a visible instruction, Escape/Tab cancellation and focus recovery. Save only
after key release; show failures without replacing the displayed binding. Include
Restore defaults, unavailable-binding warnings and local persistence guidance.
Reading holds keyboard-reading help, estimated JLPT badge visibility and local
translation selection. Sources & licenses has its own
window with linked attribution and packaged notice guidance. No nonfunctional settings drawn merely
to match the reference sidebar. Use native secondary-window decorations for
move/resize/minimize/close accessibility; toolbar and popup use their compact chrome.
Close hides the secondary window; explicit Quit stays on the toolbar.
The Sources window uses the English app name without a slogan or Japanese app-name
subtitle. Preserve the source descriptions, attribution and full licence text.

Keep concise JMdict/KANJIDIC2 source and CC BY-SA attribution with dictionary
content, and preserve the full sources/licenses entry point. Disclosure must not
make required notices inaccessible.

## 6. Implementation and accessibility acceptance

Use plain React/CSS with semantic variables and shared primitives under
feature-owned selectors. Keep
transparent backgrounds explicitly scoped to capture, overlay, toolbar and
popup roots; opaque surface components set their own backgrounds. A global
background rule must not paint over manga. Do not add Tailwind, a component kit,
a state library or a remote font dependency without a specific need.

Keep native window sizing parameters named and tested in Rust. Frontend tokens
govern visual layout, but native physical dimensions and actual viewport remain
authoritative for capture/overlay transforms. A few documented matching layout
constants are preferable to a new token-generation pipeline at this scale.

During implementation, verify:

1. Keyboard tab order, visible focus, Enter/Space activation, Escape and focus
   restoration across toolbar, regions, popup, disclosure and secondary views.
2. Correct accessible names/pressed/expanded states and live status announcements;
   loading does not move focus or replace the sentence.
3. Measured contrast, offline font fallbacks, Japanese glyphs and multiline text
   on macOS and Windows. Uncertainty/error/selection cues do not rely on color alone.
4. Compact and expanded window bounds, narrow/small work areas, long sentences,
   all word/kanji states, missing data, and alternative-match saving.
5. Native pass-through, display scaling, capture exclusion and work-area clamping
   through the platform checks in [UI testing](ui-testing.md).

Use synthetic Japanese text/regions for public screenshots and tests. Local
reference manga images guide composition only; do not redistribute them as app
assets or golden test snapshots.

## 7. Tray and menu bar behavior

Keep the toolbar visible on ordinary startup. Create one application-owned tray
icon per running process, independent of React window mounts. Hiding the toolbar
is an explicit action and lasts only for the current run.

| Menu item                   | Behavior                                                                                                                                                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Show Toolbar / Hide Toolbar | Label reflects actual toolbar visibility. Show restores, clamps to a connected display's work area, unminimizes and focuses the existing toolbar. Hide dismisses its overflow menu and hides the toolbar. |
| Show OCR results            | Restores the latest hidden completed result without OCR, toolbar activation or keyboard focus changes. Disabled without retained results, during scans and while results are already shown.               |
| Saved                       | Opens the existing Saved window.                                                                                                                                                                          |
| Settings                    | Opens the existing settings view.                                                                                                                                                                         |
| Sources & licenses          | Opens the existing attribution window.                                                                                                                                                                    |
| Quit YomiMado               | Uses the existing application exit and OCR cleanup path.                                                                                                                                                  |

Use native separators between toolbar visibility, secondary windows and Quit.
The tooltip is `YomiMado`. Keep this first menu small; scan modes, rescan and the
overlay visibility toggle remain in the toolbar. **Show OCR results** reuses the
same display-validation and overlay reveal path as the toolbar. Keep its enabled
state synchronized with scan/result visibility transactions, and recheck active
scans when dispatched. Repeated queued Show requests are no-ops after restoration;
never navigate a visible overlay again or restore its old popup.

Platform interaction:

- macOS: clicking the icon opens the native menu. Use a dedicated transparent
  monochrome template icon derived from the app mark, checked in light and dark
  menu bars and on Retina displays. Keep the current Dock behavior.
- Windows: left-click release shows/focuses the toolbar; right-click opens the
  native menu. Use a small transparent app icon that remains legible in light
  and dark taskbars at 100%, 125%, 150% and 200% scaling. The notification-area
  overflow may contain the icon; users can pin it through Windows.

Hiding the toolbar leaves existing OCR overlays as they are. It does not clear
results, trigger OCR, suspend the local service or unregister shortcuts. Document
this beside the toolbar visibility control. Existing keyboard shortcuts remain
available while the toolbar is hidden.

During an active selection/capture/OCR session, disable toolbar visibility,
result restoration and secondary-window tray actions. Keep Quit available. Recheck the scan guard when
an action executes, because state can change after a menu opens. A Windows
left-click during capture must not reveal the toolbar into a screenshot or steal
selector focus. Refresh menu state whenever scans or toolbar visibility change.

Closing Settings, Saved or Sources keeps its existing hide-on-close behavior.
Do not introduce automatic hiding on toolbar close or intercept every app exit.
Quit from the tray, toolbar and normal OS app-quit routes must share cleanup.

If tray creation fails, retain the visible toolbar and its Quit action. Offer
Hide Toolbar only when tray recovery is available, and report native failures
through the toolbar status control. Ownership stays in Rust for the app lifetime.
See [tray verification](ui-testing.md#tray-verification-and-acceptance) and the
[source/license review](../THIRD_PARTY_LICENSES/system-tray-review.md).

Login autostart, tray-only startup, hiding the Dock icon, notifications, animated
icons, direct tray capture, single-instance enforcement and persisted toolbar
visibility remain separate enhancements.

## Icon provenance and regeneration

The current icon uses a copper capture window, a blue upper-right corner bracket
and a white manga page on a charcoal tile. Two vertical marks suggest Japanese reading; an offset page edge
adds depth. Transparent padding remains outside the rounded tile.

The current master is `apps/desktop/src-tauri/icons/source-v3-copper-blue.png`,
recolored with the built-in imagegen tool on 2026-10-22 using the palette above.
Its transparent outer padding is retained. The preceding blue master,
`apps/desktop/src-tauri/icons/source-v2-blue.png`, remains as provenance.
The original copper/ivory master, `apps/desktop/src-tauri/icons/source-v1.png`,
was generated with the same tool on 2026-10-04 and remains as provenance.
No font, third-party logo, manga image or model asset was used as an input.

Tauri's existing CLI generated the PNG sizes, Windows ICO/Store assets, and
macOS ICNS. The main Tauri configuration references the desktop icons; the
macOS release configuration inherits them. Only desktop icon assets are kept
in this repository.

To regenerate the desktop exports from the master, run from `apps/desktop`:

```sh
rtk npm run tauri -- icon src-tauri/icons/source-v3-copper-blue.png --output /tmp/yomimado-icons-copper-blue
```

Copy only the top-level desktop files from that output into
`src-tauri/icons/`; the CLI also produces mobile subdirectories, which are
outside YomiMado's scope. Keep the master at its original resolution and
preserve its alpha channel. Review the 32px export after any design change.

### Tray marks

The tray uses separate small geometric exports of the same capture-window/page
idea, drawn by `scripts/generate_tray_icons.py`. This source defines the shapes
and colors directly; it uses no fonts, third-party artwork or extra libraries.
Run `python3 scripts/generate_tray_icons.py` from the repository root to regenerate:

- `tray-template.png`: transparent 36 × 36 black mark, displayed by the native
  macOS status item at 18 logical points with template adaptation.
- `tray-windows.png`: transparent 32 × 32 copper/white mark with a blue bracket.

These assets are embedded in Rust and do not replace the desktop app icons.
Inspect the actual icons in light/dark system UI at supported display scales.

### Copper and blue recolor prompt

The built-in imagegen tool edited the preceding blue master with transparent
output. Tauri generated the current desktop exports.

```text
Use case: precise-object-edit.
Asset type: local trial YomiMado desktop app icon.
Edit target: the provided existing source-v2-blue.png app icon.
Primary request: change the large capture-window frame ONLY to copper #D98B5F, while changing the separate offset upper-right corner bracket ONLY to primary blue #0080FF. The main frame must be copper throughout; the detached/offset top-right bracket must be blue throughout. Keep the manga page white #F2F4F8. Set the charcoal rounded-square tile to #1A1D24, with dark inner area and reading marks #131519.
Constraints: preserve all existing shapes, geometry, position, proportions, round corners, original silhouette, canvas size and page depth. Color palette edit only. No new objects, text, badges, outlines, added gradients or new shadows. Preserve genuine transparent padding outside the rounded-square tile and all alpha. Output one square icon matching source resolution if possible.
```

### Previous blue recolor prompt

The edit target was the original master; the built-in imagegen tool supplied the
preceding blue recolor with transparent output.
The tray generator uses the same palette directly, while the macOS template
remains monochrome for system adaptation.

```text
Use case: precise-object-edit. Asset type: production desktop app icon recolor.
Edit target: the supplied existing YomiMado app icon.
Change ONLY its palette to match the app's new charcoal and #0866FF blue theme.
Recolor the copper/orange capture-window frame and offset top-right corner to vivid blue #0866FF;
recolor the warm charcoal rounded-square tile and the two vertical reading marks to cool charcoal #171B22 / #10141B;
recolor the ivory page to cool white #F4F7FF.
Preserve the existing recognizable symbol, all geometry, proportions, exact positioning, rounded corners,
side page edge, subtle depth, clean silhouette and original square canvas.
Preserve the original transparent padding outside the rounded tile, with genuine alpha, not a checkerboard.
Color change only, no redesign, no new elements, no text, no logos, no gradients added, no outer shadow.
Keep edges crisp and the symbol legible at 32 pixels.
Output one square icon at the source resolution if possible.
```

### Original generation prompt

```text
Use case: logo-brand
Asset type: production desktop app icon for YomiMado, a Japanese manga reading assistant.
Primary request: create one polished, distinctive app icon expressing a reading window onto a manga page. Keep the existing app palette: warm charcoal #25211e, copper #df8259, and warm ivory #f8f6f1.
Subject: a bold copper rounded window frame surrounding a warm ivory manga page. Two distinct vertical charcoal pill-shaped marks on the page suggest vertical Japanese reading. A subtle offset page edge adds depth. The frame should have an elegant small opening or layered corner that evokes the capture/overlay function. Simple cohesive symbol, not a collection of objects.
Style: precise geometric vector-like shapes, crisp edges, flat colors, exceptionally restrained depth. Friendly, calm, professional macOS and Windows application icon.
Composition: single centered icon on a warm charcoal rounded-square tile. Tile occupies about 84% of a square 1024x1024 transparent canvas with consistent transparent padding, generous inset around the central symbol. Strong silhouette, thick frame, legible at 32px. Straight-on view.
Constraints: one icon only, no mockup, no lettering, no Japanese glyphs, no labels, no watermark, no external shadow, no photographs, no characters or faces, no extra decorative sparkles, no gradients. Outside the rounded-square tile must be truly transparent.
```
