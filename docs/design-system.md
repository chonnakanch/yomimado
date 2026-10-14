# YomiMado design system

Status: **Approved by the owner on 2026-10-13.** Prepared 2026-10-13.
Companion architecture and rollout: [UI redesign plan](ui-redesign-plan.md).
Phase 1 implements the tokens and floating-toolbar controls; the approved Phase 2
implements OCR region states and keyboard entry, with native platform acceptance
still required. The owner authorized Phase 3 on 2026-10-14; the Compact dictionary
popup specifications below are implemented and accepted in the running macOS
development app. The Phase 4 Saved library is accepted. Phase 5 Settings categories
and the shared secondary shell are implemented for review.

## 1. Visual direction and boundaries

Use the supplied local images in `docs/design-references/` for compact utility
window composition, Japanese sentence/word hierarchy and restrained dark
surfaces. Use the written palette and feature list as the source of truth.
The detailed popup image's disclosure rhythm is useful; its audio, conjugation
tables, example sentences and related-word features are outside this scope.

Keep the original manga visible. Opaque surfaces belong to the toolbar, popup
and secondary window. The OCR layer remains transparent except for outlines and
very light hover/selection fill. No manga image, full-screen dimmer, translation
replacement, loud status banner or decorative motion in the reading view.

Jisho-inspired means a readable headword, reading, base form, POS and numbered
definitions. It does not mean copying Jisho assets or implying the existing
service exposes every Jisho field.

## 2. Semantic color tokens

Declare tokens centrally in `apps/desktop/src/styles/tokens.css`; component
styles consume roles, never repeat hex values. The palette below is implemented in Phase 1.

| CSS token                      | Value                       | Role                                                    |
| ------------------------------ | --------------------------- | ------------------------------------------------------- |
| `--color-background`           | `#181818`                   | Secondary-window canvas; dark text on filled accents.   |
| `--color-surface`              | `#242220`                   | Toolbar, popup, collection rows and settings surfaces.  |
| `--color-surface-elevated`     | `#302C29`                   | Overflow menu, disclosure panels and hovered controls.  |
| `--color-accent`               | `#D97F5C`                   | Primary action, region default outline and links.       |
| `--color-accent-hover`         | `#E88762`                   | Primary action hover and region hover outline.          |
| `--color-selected`             | `#75A5EB`                   | Chosen token, active region and focus ring.             |
| `--color-text-primary`         | `#F5F2EF`                   | Japanese and primary UI text.                           |
| `--color-text-secondary`       | `#B9B1AB`                   | Readings, metadata and supporting text.                 |
| `--color-text-muted`           | `#A8A29E`                   | Dates, secondary hints and compact attributions.        |
| `--color-border`               | `#514943`                   | Surface separators and quiet decorative borders.        |
| `--color-success`              | `#7FB58B`                   | Explicit saved/installed feedback, paired with words.   |
| `--color-on-accent`            | `var(--color-background)`   | Text/icon on filled orange or blue action.              |
| `--color-focus`                | `var(--color-selected)`     | Keyboard outline independent of hover.                  |
| `--color-status-error`         | `var(--color-accent-hover)` | Error text/icon with explicit message, not color alone. |
| `--color-region-default`       | `var(--color-accent)`       | Ordinary OCR polygon.                                   |
| `--color-region-hover`         | `var(--color-accent-hover)` | Hovered OCR polygon.                                    |
| `--color-region-selected`      | `var(--color-selected)`     | Selected OCR polygon.                                   |
| `--color-region-hover-fill`    | `rgb(217 127 92 / 0.08)`    | Minimal hover wash above manga.                         |
| `--color-region-selected-fill` | `rgb(117 165 235 / 0.10)`   | Minimal selected wash above manga.                      |

Filled accents use dark text, not small white labels. Secondary controls use
primary text on elevated/surface backgrounds. Verify normal text contrast ≥4.5:1
and large text ≥3:1. The quiet border is not sufficient as the sole affordance or
focus indicator: use readable labels/icons and the blue focus ring. Check controls
and focus against a ≥3:1 target, including hover/selected states. These are design
acceptance targets; measure actual composited styles during implementation.

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

Proposed font stacks:

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

No new font is bundled or downloaded in the initial slice. The named fonts are
preferred when installed; native fallbacks must work fully offline on both
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
| `--radius-window`     | 12 px            | Toolbar/popup/menu surface.                    |
| `--control-compact`   | 32 px            | Small menu and token-adjacent actions.         |
| `--control-default`   | 36 px            | Toolbar/settings action height.                |
| `--popup-width`       | 420 px           | Preferred logical width; work-area clamp wins. |
| `--popup-padding`     | `var(--space-4)` | Single outer padding.                          |
| `--popup-section-gap` | `var(--space-6)` | Distinct content sections.                     |
| `--focus-width`       | 2 px             | Visible focus outline, 2 px offset.            |
| `--motion-fast`       | 120 ms           | Color/fill feedback only.                      |

Toolbar starts around 520 × 56 logical px, compact around 224 × 48 after the
owner's 2026-10-14 refinement. Compact mode retains both scan icons, Rescan,
overlay visibility/status and expand on one row. These are
layout targets, not fixed minimums that can clip labels. Popups grow naturally
until their work-area cap (roughly 70% height), then scroll the details. At narrow
widths stack reading/metadata below the word, wrap footer actions and retain
Japanese type size. Clamp native positions to actual work area with a 12 logical
px screen inset and 8 logical px anchor gap, reusing tested placement behavior.

Use one quiet shadow for popup/menu/toolbar where safe; do not add a native
Windows overlay shadow that shifts the geometry. Surface borders are 1 px;
focus and selected outlines are distinct from those decorative borders.
Suppress transitions under `prefers-reduced-motion`. No window-position animation,
scale animation or repeated pulsing while OCR is running.

## 5. Component specifications

### FloatingToolbar and ScanModeButton

One restrained surface; separate drag handle from buttons. Use short text for
Selected Area and Whole Screen, with a simple 16–20 px icon where useful.
Rescan and Hide/Show may use icons with accessible names and focusable tooltips.
Do not infer meaning from an icon alone. The model-install action belongs in
Scan & OCR; missing models/errors use a warning icon with details and a setup
link shown only when requested.

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

| State              | Stroke                | Fill            | Additional cue                                              |
| ------------------ | --------------------- | --------------- | ----------------------------------------------------------- |
| Default            | 1 CSS px orange       | Transparent     | Region orientation in accessible label.                     |
| Hover              | 2 CSS px accent-hover | Orange at 8%    | Pointer cursor, no lookup triggered.                        |
| Selected           | 2 CSS px blue         | Blue at 10%     | Selected semantics and keyboard focus if active.            |
| Review/approximate | Same state colors     | Same state fill | Dashed stroke and “Review OCR” / “Approximate region” text. |
| Demo               | Dashed outline        | Transparent     | “Demo boundary — no recognized text.”                       |

Use `vector-effect: non-scaling-stroke`. Keep original polygons; the component
name does not justify reducing geometry to a rectangle. Region fill/hit area
can remain clickable while visually transparent. Label uncertainty explicitly;
unknown confidence must never become a percentage badge. Apply selected color
after hover styling so hovering a selected region does not erase selection.

Native hit routing is an independent requirement in the architecture plan.
`pointer-events` only selects DOM targets; visual transparency alone is not proof
that underlying applications receive input.

### DictionaryPopup and ClickableSentence

The first view contains the Japanese sentence, Copy sentence and Save sentence,
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

The hidden correction editor opens through **Edit OCR text**. Use a labeled
Japanese textarea only in that state, with Apply/Analyze and Cancel. Keep the
applied sentence visible until editing is committed, and reset all dependent
lookup/translation/save states on commit. Review warnings point to this action.
Demo text is identified and never treated as recognized Japanese.

### WordDefinition and AlternativeDictionaryMatches

Order: selected surface, hiragana reading, base form, morphological POS,
numbered English senses, entry-specific Save word, attribution. Base form can be
an inline labeled field, even when equal to surface; no fabricated inflection
table. POS is supplied by Sudachi, not the dictionary senses. Do not generate
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
existing English output and cached state only after a request. Both the Japanese
and English remain accessible; changing source clears stale output.

### Saved collections and SettingsWindow

Secondary navigation has one **Saved** entry with **Words** and **Sentences** tabs
inside the library, alongside Settings. Use
compact readable rows with expandable context rather than wide fixed tables
that require horizontal scrolling. Keep local dates, existing stored order,
refresh/error/empty states and confirmed Remove actions. Lists remain readable
with larger text and narrow windows.

Settings uses ordinary labeled controls for actual capabilities. Scan & OCR holds
verified detector status/import/replacement and capture/shortcut guidance;
Reading holds the existing estimated-order switch; About/Sources retains linked
attribution and packaged notice guidance. No nonfunctional settings drawn merely
to match the reference sidebar. At the owner's request on 2026-10-14, the secondary
window uses app-owned, labeled Minimize, Maximize/restore and Close controls.
Dragging the brand area moves the window; native edge resizing remains available.
Close hides the secondary window; explicit Quit stays on the toolbar. Keep all
three controls on one row at narrow widths and report native action failures.

Keep concise JMdict/KANJIDIC2 source and CC BY-SA attribution with dictionary
content, and preserve the full sources/licenses entry point. Disclosure must not
make required notices inaccessible.

## 6. Implementation and accessibility acceptance

Retain plain React/CSS. Extract styles gradually from `styles.css`, using
semantic variables and shared primitives with feature-owned selectors. Keep
transparent backgrounds explicitly scoped to capture, overlay, toolbar and
popup roots; opaque surface components set their own backgrounds. A global
background rule must not paint over manga. Do not add Tailwind, a component kit,
a state library or a remote font dependency for this change.

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
   through the platform checks in [the architecture plan](ui-redesign-plan.md).

Use synthetic Japanese text/regions for public screenshots and tests. Local
reference manga images guide composition only; do not redistribute them as app
assets or golden test snapshots. The owner approved the design and limited initial implementation to tokens
and toolbar. Review of that result gates further work; exact-installer acceptance
remains separate future work.
