# YomiMado UI/UX redesign plan

Status: **Approved by the owner on 2026-10-13. Phase 1 approved for continuation; Phase 2 implemented for review.**
Prepared 2026-10-13 against `develop` at `4f8a395` (app version `0.1.0`).
The owner approved this plan and [the design system](design-system.md), then
authorized Phase 1: design tokens and the floating toolbar, then Phase 2: OCR
regions and native input routing. Later phases require approval of that result. No installer publication is authorized.

## 1. Goal, scope and reference interpretation

Make YomiMado a compact companion above the user's existing manga reader:
**capture → recognize → click → learn**. The dictionary popup is the highest
product priority. Keep React, TypeScript, Tauri 2, the Rust capture boundary and
the local Python services. The app does not become a manga viewer.

The owner supplied three local visual references in `docs/design-references/`:

| File                                                     | Direction to carry forward                                                                                                   |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `YomiMado OCR Translation UI Concept.png`                | Movable compact toolbar; two explicit capture actions; subtle orange/blue boxes; secondary library/settings window.          |
| `a_clean_ui_ux_concept_poster_mockup_image_of_a_d.png`   | The same overall utility-window composition and restrained dark surfaces.                                                    |
| `a_clean_ui_ux_mockup_composite_screenshot_of_a_man.png` | Persistent full sentence above a prominent selected word, reading and grouped definitions; disclosure for supporting detail. |

All three images were inspected. Treat them as composition references, with the
written request taking precedence. Omit their speaker controls, automatic
translation, romanization, generated conjugation tables, example-sentence
corpus, related-word expansion, confidence sliders and unsupported model/language
selectors. Existing APIs do not provide those latter features. Example compounds
are the existing JMdict kanji compounds, not invented example sentences.
The images remain user-local, untracked reference files; do not bundle them or
commit their manga imagery as public fixtures without suitable rights.

In scope: floating toolbar, Selected Area and Whole Screen, Rescan, reversible
overlay visibility, sentence-first dictionary popup, word/kanji details, explicit
copy/save, saved collections and settings. No automatic hover scanning,
continuous scanning, audio, JLPT/WaniKani badges, Wikipedia, stroke counts,
flashcards or spaced repetition. Do not add Linux or mobile targets.

Retain existing on-demand local translation and OCR correction through secondary
actions. Preserve optional estimated reading-order navigation, off by default,
without promoting it to a third scan mode. Retire automatic page cropping from
the redesigned user flow: it is neither Whole Screen nor Selected Area. Keep
its tested backend helper initially, rather than deleting working OCR-adjacent
logic during the visual refactor. This changes the old page-scan shortcut's
meaning and requires updated usage documentation.

## 2. Existing architecture and behavior

### Windows, UI and state

`apps/desktop/src/main.tsx` selects four React roots by URL query: main,
capture, overlay and translation. Each webview owns its own React `useState`
and effects; there is no shared React store, router or UI framework.

| Current surface      | Implementation and behavior                                                                                                                                                                                                                                                |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Main                 | `App.tsx`, configured as a resizable 700 × 480 window. Contains model import/replacement, manual selection, automatic manga page scan, reusable area configuration, reading-order setting, sources/licenses and saved word/sentence lists.                                 |
| Selection/processing | `features/capture/CaptureSelector.tsx`. Drags a rectangle, invokes native capture, calls OCR, optionally sorts manga regions, opens the overlay and closes itself. `scan=auto` tries page detection, then saved area, then asks for a drag. `scan=configure` saves a drag. |
| Diagnostic capture   | `CaptureDebugView.tsx`, gated by `VITE_CAPTURE_DEBUG=1`. In-memory screenshot and geometry preview for development, not a normal manga-viewing feature.                                                                                                                    |
| OCR interaction      | `features/overlay/OcrOverlay.tsx`. Reads `get_overlay_state`, maps polygons into the measured webview viewport, handles region clicks, review/demo indications and optional estimated navigation. Contains a small attached strip, not a persistent floating app toolbar.  |
| Learning popup       | `features/translation/TranslationPopup.tsx`. Separate native popup, with OCR textarea, tokenized sentence, selected-word entries, kanji buttons/details/compounds, saving and explicit local translation in one large component.                                           |

The popup already tokenizes genuine OCR text on opening and does **not** request
word meanings until a token is clicked. It has Unicode code-point-aware sentence
reconstruction and request IDs that stop stale lookup/save/translation results
from replacing newer state. Individual kanji are selected within the chosen
word; there are no character boxes on the manga itself. It currently displays
all returned word matches and fetched compounds without disclosure, and repeats
sentence context in the kanji section. Copy sentence is not implemented.

`styles.css` contains global styles and hardcoded warm dark colors, with many
popup labels around 10–13 px. It has transparent root/background exceptions for
the native utility windows, but no semantic token system. The requested audio,
badge, Wikipedia and stroke-count controls are absent from the inspected UI;
keep them absent rather than adding integrations to remove later.

### Native capture and window lifecycle

`src-tauri/src/lib.rs` manages xcap capture, shortcuts, detector availability,
the packaged Python process and `OverlayStore`. The capture selector and OCR
overlay are borderless, transparent and always on top; the dictionary popup is
also always on top and explicitly focused after a region click.

- Capture currently resolves the monitor from **the main window**, minimizes
  that window, and restores/focuses it on cancellation. This must change for a
  toolbar-driven app whose secondary window can be closed or hidden.
- Shortcuts are Cmd/Ctrl+Shift+O for manual selection and Cmd/Ctrl+Shift+S for
  the automatic page/saved-area path. Windows window creation uses async command
  dispatch; shortcut callbacks move blocking work off the Windows UI thread to
  avoid WebView2 creation deadlocks. Preserve this platform handling.
- `capture_display` already exists, but the current frontend calls it indirectly
  through `capture_auto_page`, not as a Whole Screen action. It clips against the
  actual selector bounds (including macOS menu-bar offsets). Audit this before
  promising a capture of every monitor pixel.
- `overlay/mod.rs` keeps large OCR results in native memory rather than URLs.
  Popup text/placement are encoded in its query. The popup is reused by navigation
  to avoid duplicate native labels and hides on blur. Escape closes it.
- Popup placement maps image polygons into physical screen coordinates, prefers
  right then left, clamps to monitor work area and scales dimensions. Its current
  width is 460 logical px, initial height 320; a `ResizeObserver` requests resizing
  when content expands. Native placement tests already cover small screens,
  negative origins and Retina scaling.
- The OCR overlay disables Windows shadows to prevent client-area offsets.
  The frontend uses CSS `pointer-events: none` around interactive SVG polygons.
  There is **no native cursor-ignore or native selective hit-test implementation**
  in the current code. CSS alone does not establish pass-through to other apps.

### Service boundaries, dictionary and persistence

| Existing boundary                              | Reuse and limits                                                                                                                                                                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `POST /api/v1/ocr`                             | PNG upload → detector geometry/orientation → Manga OCR crops → structured regions. Python pipeline already has retry/fallback/review behavior; leave it unchanged. Windows packaged inference uses its CPU ONNX backend.                         |
| `POST /api/v1/tokenize`                        | SudachiPy **0.6.10**, core dictionary **20250515**, split mode C. Returns original surface, reading (usually katakana), base form, POS and Unicode code-point offsets. Punctuation remains in the source but is not a study token.               |
| `POST /api/v1/word`                            | Local indexed JMdict; surface/base-form matching, reading normalization, restrictions, priority ranking and deduplication. Returns up to three matches with English glosses, match kind and reading-match flag. Do not reorder/rerank in the UI. |
| `POST /api/v1/kanji`, `/api/v1/kanji/examples` | KANJIDIC2 English meanings/on/kun readings and up to three short JMdict compounds excluding the selected word. No stroke/JLPT/WaniKani fields.                                                                                                   |
| `POST /api/v1/translate`                       | Existing local Marian provider (Helsinki-NLP opus-mt-ja-en), with SQLite cache keyed by provider/source. This is local sentence translation, not an implemented cloud/contextual provider UI.                                                    |
| `/api/v1/vocabulary`, `/api/v1/sentences`      | Explicit save/list/delete via `VocabularyStore` in SQLite; preserve tables, IDs, fields, paths, ordering and duplicate/upsert semantics.                                                                                                         |

Reuse the typed/validated clients in `src/lib/`, including the common loopback
transport and its `X-YomiMado-Client` header. Do not bypass service security or
expose Python package internals to React. Saved words contain surface, reading,
base form, chosen meanings, source sentence and timestamp; POS is not persisted.
Saved sentences optionally contain a translation. Saving does not trigger one.

Saved scan areas are in webview localStorage, keyed by display ID, physical bounds
and scale (`features/capture/scan-area.ts`). The reading-order preference is
also in localStorage and the overlay listens for storage changes. Native overlay
state is ephemeral. Do not equate any of these with a global React state.

Important data limits: word senses expose glosses, not dictionary-sense POS, so
label the existing POS as morphological analysis. Current real OCR emits
`confidence=0` for unknown confidence, usually `type="other"` and empty tokens.
Never call unknown confidence 0% accuracy or invent dialogue classifications.
Preserve `geometrySource`, `needsReview` and `reviewReason`.

## 3. Reuse and required changes

| Area          | Keep                                                                                                                            | Change                                                                                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Capture       | xcap interface, permission gate, coordinate metadata, compositor wait, PNG handling, response parsing, selection/debug behavior | Explicit target monitor; standalone scan orchestration; Selected Area saves its rectangle; Whole Screen bypasses page cropping; repeat last successful scan. |
| Overlay       | Stored regions, polygons, orientation, measured viewport transform and review metadata                                          | Reusable `OCRBoundingBox`, orange/blue states, keyboard region selection, true native pass-through, reversible hide/show instead of close-and-clear.         |
| Popup         | Token reconstruction, API clients, selection guards, ranked word entries, native positioning and explicit saving/translation    | Extract components, show the sentence once, hide editor initially, hiragana reading presentation, disclose alternatives/compounds, add copy.                 |
| Main/settings | Saved-data clients and removal safeguards; verified model import and sources/notices                                            | Secondary library/settings shell; move model management to Scan & OCR; accessible navigation and compact collections.                                        |
| Styling       | Existing React/plain CSS approach and transparent-root handling                                                                 | Semantic CSS variables, scoped primitives, readable Japanese hierarchy and shared component states.                                                          |

## 4. Proposed component and state architecture

Keep one frontend bundle with native window-specific roots. The structure below
is a target; introduce files only when the corresponding step is implemented.

```text
src/
  main.tsx                         window root selection
  App.tsx                          secondary library/settings shell
  styles/tokens.css                semantic values
  styles/primitives.css            buttons, labels, disclosure, focus, status
  components/                     small shared UI primitives only
  features/toolbar/
    FloatingToolbar.tsx
    ScanModeButton.tsx
    ToolbarMenu.tsx
  features/capture/
    CaptureSelector.tsx            keep selection/debug integration
    scan-session.ts                shared one-shot workflow, not a new engine
    scan-area.ts                   existing display-bound conversions
  features/overlay/
    OcrOverlay.tsx
    OCRBoundingBox.tsx
  features/dictionary/
    DictionaryPopup.tsx
    useDictionarySelection.ts      lookup/reset/request guards from current popup
    ClickableSentence.tsx          original text + Unicode-aware token segments
    WordDefinition.tsx
    AlternativeDictionaryMatches.tsx
    KanjiDetail.tsx
    ExampleCompounds.tsx
    SaveWordButton.tsx
    SaveSentenceButton.tsx
  features/translation/
    SentenceTranslation.tsx        existing on-demand client/output
  features/library/
    SavedWordsView.tsx
    SavedSentencesView.tsx
  features/settings/
    SettingsWindow.tsx             view inside the secondary native window
    ScanOcrSettings.tsx
```

Avoid a router/state-library dependency for a few secondary tabs. `SettingsWindow`
is a settings view in the main native shell, not a requirement for another native
window. Retain the native label `translation-popup` during initial migration;
the React component may be called `DictionaryPopup` without renaming all IPC at
once. Add a distinct native `toolbar` window and root; keep `main` secondary and
create/show it only when requested. Start the service independently of whether
the main webview is visible.

Native state should own the minimal cross-window session: current scan phase,
request/session ID, last successful scan specification, overlay visibility and
retained result metadata/regions. Send small status events to the toolbar and
offer a snapshot command when a root mounts; events alone are insufficient after
reload. React owns ephemeral popup selection/disclosure and secondary tab state.
Reuse the existing native result store; no screenshot persistence or new database.

Scan specification: `selectedArea` or `wholeScreen`, display identity, physical
display bounds and scale, plus a rectangle for Selected Area. Validate it against
the live display before reuse. Keep last successful mode in the current session;
retain existing display-bound area storage for future selection reuse. Do not
silently turn a saved area from another display/layout into a valid rescan.
If new persisted UI preferences are needed, use versioned localStorage keys for
collapse/placement and the existing setting pattern; handle storage failure.

Keep the current stale-response protections when extracting popup state. A
changed sentence clears dependent tokens, word/kanji/example choices, translation
and save status. A changed token clears the relevant entry/kanji/save state.
Expansion requests must also carry the current token/character identity.

## 5. Interaction specification

### Floating toolbar and two scan modes

Expanded toolbar: drag handle, **Selected Area**, **Whole Screen**, **Rescan**,
**Hide/Show overlays**, overflow and collapse. About 520 × 56 logical px is a
starting layout, subject to text measurement and platform verification. Collapse
to an approximately 112 × 48 strip containing a drag handle, expand control and
Rescan. Always provide a keyboard-expand path and access to Quit via expansion.
The native bounds must shrink with the content; an invisible expanded window
must not intercept the manga. Overflow contains saved collections, settings,
optional region navigation and Quit. Missing-model status links to Scan & OCR.

Define the target explicitly: toolbar buttons scan the monitor containing the
toolbar; global capture shortcuts target the monitor under the pointer. Display
the target's name in a tooltip/status. Each scan locks its target at initiation.
Rescan uses the original successful specification even if the toolbar moves.
If that display disappears or its geometry/scale changes, prompt a fresh
selection/Whole Screen action rather than guessing.

- **Selected Area:** drag on one monitor, capture and recognize on release.
  Store the successful physical rectangle for Rescan. A drag cannot span monitors.
- **Whole Screen:** capture that monitor without page detection or a crop based
  on a saved area; OCR once. Use existing `capture_display` plumbing, but correct
  any selector-offset limitation needed to represent the full physical monitor.
  Respect existing size/decoded-image limits and offer Selected Area on overflow.
- **Rescan:** recapture fresh pixels using the last successful mode/area. It never
  reruns OCR on a stored screenshot. Disabled before a successful scan.
- **Hide overlays:** hide result windows and popup, disable region hit targets,
  retain native OCR result and last scan. **Show overlays** restores the result
  without OCR and warns that it may be stale after the underlying page changes.
  Hide/show is independent of scanning mode and never starts a scan.

Keep Cmd/Ctrl+Shift+O for Selected Area. Propose Cmd/Ctrl+Shift+S for Whole Screen,
with a visible migration note from the old page-scan behavior. Do not invent
new global shortcuts from those drawn in the reference images.

Lifecycle: idle → selecting/capturing → recognizing → ready/no-text/error.
Allow one active scan; repeated button/hotkey activation does not create competing
selectors/results. Disable scan actions while busy. Hide all app utility windows
before screenshotting, including a visible secondary window, and restore intended
visibility afterward. Preserve the native compositor wait. Cancellation restores
the previous result visibility and toolbar without opening/focusing the main
window. A cancelled/failed scan must not publish late results or overwrite the
last successful specification. OCR need not be forcibly interrupted to discard
a cancelled request. Show errors and retry actions on the toolbar after selector
closure; the invisible processing surface must not block the underlying reader.

### Overlay and focus

Default thin orange outline with transparent fill; hover stronger orange and
subtle fill; selected blue and subtle blue fill. Keep polygons rather than
replacing geometry with guessed rectangles. Vertical and horizontal regions use
the same transform path. Review/approximate states remain dashed with a readable
explanation in the popup/status, including when the selected outline is blue.

All space outside region hit areas must route clicks, drags and scroll to the
underlying browser/app. The toolbar and popup remain separate native interactive
windows. Test actual cross-process event routing, not just DOM pointer events.
Do not add an opaque full-screen backdrop to the dictionary popup.

Before the overlay refactor, prototype a small native input-routing adapter on
both platforms. Evaluate native hit-test/shape routing first. If the pinned stack
cannot supply it, evaluate native cursor-position sampling plus whole-window
cursor-ignore toggling against the known polygons. This fallback uses geometry
only, never OCR or dictionary requests on hover. Do not rely on DOM mouseenter
to reenable an ignored window. Measure fast-entry click loss, sampling latency,
CPU use and browser scrolling. Whole-window ignore is not itself a selective
hit-test API; multiple per-region webviews are not the default design. The
adapter choice remains an implementation investigation, with pass-through a
blocking acceptance requirement, not a claimed existing capability.

Keyboard access must remain available even if the region layer is click-through:
offer an explicit Focus regions action in overflow, a focused region navigator,
and Enter to open it. This is keyboard navigation, not automatic panel reading
order. Give SVG regions labels, focus/selection semantics and Enter/Space
activation. Optional estimated-order controls retain their setting and label.
Escape closes the focused popup; Escape in region navigation hides the overlay.
Do not register a global Escape that would disrupt the reader.

Open/focus the popup only on explicit region activation; ordinary scan completion
must not take keyboard focus from the reader. Preserve blur dismissal and reusable
labels. When the popup closes through keyboard action, return focus to the
region navigator that opened it; clicking elsewhere must leave focus there.

### Dictionary popup: highest priority

Default view: persistent full Japanese sentence, Copy sentence, Save sentence,
close control and a quiet “Select a word” instruction. Tokenize locally once on
open; render the source immediately during loading. No automatic word/kanji/
translation lookup. Show no duplicate OCR textarea. Keep punctuation, gaps,
line breaks and Unicode code points intact.

Selecting a token shows its surface at 28–32 px, hiragana reading, base form,
morphological POS and the first ranked dictionary match's numbered English
definitions. Preserve match warnings (“Matched base form”, reading mismatch)
and possible-sense wording. Put other matches in **Alternative dictionary
matches (N)**, collapsed initially, with an explicit entry-specific Save action.
Saving a displayed entry retains that entry's readings/senses and the sentence;
do not combine definitions from different matches. If none is available, retain
Save without meaning and clearly show missing/unavailable dictionary state.

Hiragana is a presentation conversion of the available kana reading; keep raw
API/save values and matching behavior. Do not guess readings or split a
whole-word reading per kanji. Label POS as token analysis, not JMdict sense POS.

Select individual kanji via dedicated character buttons in the selected word's
detail, avoiding nested buttons in sentence token controls. Kana-only words show
no kanji section. A selected kanji reveals English meanings, on'yomi and kun'yomi.
Keep on'yomi conventionally katakana and kun'yomi as supplied. **Example compounds**
is collapsed; request them when first expanded and reuse while that character
and token remain selected. Missing compounds must not hide valid kanji details.
All these operations retain the full sentence and allow switching words in place.

Secondary **Edit OCR text** reveals the existing correction editor with explicit
Apply/Analyze and Cancel. Applying changes retokenizes and clears stale dependent
results; Cancel keeps the last applied sentence. Show a review indication for
uncertain/approximate OCR and make this correction action discoverable.
Secondary **Translate locally** retains current on-demand translation/cache,
displaying the original Japanese alongside the requested English result.
Save sentence includes a translation only if it belongs to the current text.
Copy sentence uses the current applied source; handle clipboard failure visibly.
Try the existing webview Clipboard API on both targets before proposing another
plugin; any new dependency needs exact-version/license review.

Use a roughly 420 logical px popup width, clamped to work area; grow only as
needed, up to roughly 70% of available logical work-area height. Reuse the native
placement math and work-area lookup, updating tested constants deliberately.
Keep sentence/actions visible with a bounded scrollable details area. Very long
sentences may scroll within the sentence section rather than consuming all space.
Handle minimum usable sizes by stacking sections, not shrinking Japanese type.

### Secondary library and settings

One native secondary window with Saved words, Saved sentences and Settings views.
Opening settings routes directly to the requested category. Closing it hides or
destroys this secondary surface without ending the service or reading session.
Toolbar overflow provides a persistent recovery/quit path; do not require a tray
integration to complete the first redesign slice.

Collections reuse list/delete APIs and stored ordering. Show readable surface,
reading, meanings and expandable source/date for words; Japanese and any saved
translation for sentences. Retain refresh, empty/loading/error states, dictionary
attribution and remove confirmation. Refresh on reopening, with an optional small
save event to refresh an already-visible collection. No schema migration, tagging,
export, flashcards or pagination backend is required by this redesign.

Settings categories stay limited to working features: Scan & OCR (existing
model status/select/replace, capture permission guidance, shortcut descriptions),
Reading (existing estimated-order switch) and About/Sources (attribution and
packaged notices). Do not turn developer environment variables or detector
heuristics into fictional user-configurable controls. The model stays
user-installed with existing checksum checks and restart/error semantics.

## 6. Cross-platform risks and verification gates

| Risk                                     | Required mitigation/evidence                                                                                                                                                                                                        |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Native pass-through                      | Validate first on macOS and Windows against another process: pointer inside/outside polygon, fast crossing clicks, wheel/trackpad scroll, browser drag/text selection, keyboard and overlay hide/show. DOM tests cannot prove this. |
| Windows WebView2 creation/frame geometry | Preserve async window creation and off-UI-thread shortcut dispatch; keep overlay shadow handling; verify first click and repeated opens without deadlock or duplicate labels.                                                       |
| Retina/Windows DPI                       | Reuse `coordinates.ts`, native physical layout, measured viewport and scan-area transforms; test 1×/2× and Windows 100/125/150/200%, monitor offsets and mixed DPI. Do not scatter new multipliers through components.              |
| Multi-monitor target/reconfiguration     | Native monitor identity and fresh physical bounds; target at scan start; reject stale rescan areas; test left/above-primary origins, disconnect/reconnect and moving toolbar between scales. No cross-monitor drag capture.         |
| Whole Screen coverage                    | Compare capture pixel bounds to full target monitor; test macOS menu bar/Dock and Windows taskbar, permission failure and image-size rejection. Do not silently report a clipped selector area as the entire monitor.               |
| macOS transparency, Spaces/full-screen   | Preserve current private-API configuration; test toolbar/overlay stacking in ordinary and full-screen readers, Mission Control and Space changes. Always-on-top alone is not verified coverage of every Space.                      |
| Capture contamination                    | Hide toolbar/popup/old overlay/secondary window before xcap; verify screenshots contain only the reader using local/synthetic fixtures. Restore windows and focus on success/error/cancel.                                          |
| Popup edges/focus/resize                 | Work-area clamping including negative origins; test top/bottom/left/right and small displays; no ResizeObserver feedback loop, focus steal on expansion or accidental dismissal while browsing.                                     |
| App lifetime                             | Secondary-window close does not exit; Quit exits and cleans up macOS child/Windows service job. Global shortcuts still work with main hidden; reopening settings is reliable.                                                       |
| Unicode/font/accessibility               | Hiragana conversion only where known, original sentence offsets preserved; fallbacks offline; keyboard controls, screen-reader labels, contrast and non-color review indicators.                                                    |

Tauri documents whole-window cursor-ignore and native window dragging; their JS
calls require explicit permissions beyond the window defaults. See
[cursor-ignore](https://v2.tauri.app/reference/javascript/api/namespacewindow/#setignorecursorevents)
and [dragging](https://v2.tauri.app/reference/javascript/api/namespacewindow/#startdragging).
These APIs establish available primitives, not evidence that selective input
routing works in this app. Prefer Rust-owned hit routing; if JS calls are used,
grant only the needed operations to the corresponding window labels. Current
`capabilities/default.json` lists only the four existing windows and explicit
close permission; new toolbar labels/operations require deliberate review.

## 7. Implementation sequence after approval

1. **Approve this plan and design system.** Confirm two-mode migration, secondary
   translation/correction, target-monitor policy and native pass-through gate.
   No application changes precede approval. No version/publication decision is
   implied by planning approval.
2. **Establish baseline and native feasibility.** Run current frontend/service/
   Rust checks. Prototype pass-through and window lifetime/monitor routing on both
   targets with synthetic regions. Stop broad overlay work if actual browser
   interactions fail; revise the adapter design rather than claiming CSS success.
3. **Implement tokens and small primitives.** Add scoped CSS variables, typography,
   button/focus/status/disclosure rules; preserve transparent roots. Verify contrast
   and offline font fallback. No new framework or font download is required.
4. **Build toolbar and scan session.** Introduce native toolbar/root, explicit
   Selected Area/Whole Screen, scan status, target snapshot, successful-area
   Rescan and cancel/error restoration. Remove capture's main-window dependence.
   Verify window bounds actually collapse and captures exclude app chrome.
5. **Refactor overlay.** Integrate the validated native input adapter, use
   `OCRBoundingBox` with tokenized states, reversible visibility, review labels
   and keyboard region entry. Preserve polygon/scale tests and OCR API parsing.
6. **Deliver dictionary popup before secondary-window polish.** Extract current
   selection guards and sentence segmentation; add sentence-first view, readable
   word/reading/POS/definitions, alternative-match disclosure, kanji and lazy
   compounds. Add copy and retain explicit save, correction and translation.
   Test rapid token changes, old responses, missing dictionaries and long text.
7. **Refactor saved collections.** Extract list views, reuse storage/confirmations,
   refresh after explicit saves/reopen, retain attribution and dates. Verify older
   saved databases still read and duplicates behave identically.
8. **Finish settings and lifecycle.** Move detector status/import/replacement to
   Scan & OCR; preserve source/licenses and reading-order switch. Make secondary
   close/reopen and explicit Quit reliable on both targets; update usage/help and
   shortcut migration text.
9. **Verify and record source readiness.** Run the checks below, inspect compact
   and expanded layouts on both platforms, and update `implementation-plan.md`
   only when implementation milestones are actually completed. Commit focused
   verified changes and push the tracked branch, excluding user-local references.
   Installer work follows the exact-candidate gates separately.

Implementation checks (not claimed as performed by this planning task):

- Frontend: existing Vitest suites, TypeScript, Prettier and Vite build through
  `npm test`, `npm run typecheck`, `npm run format:check`, `npm run build`.
- Extend meaningful behavior tests for default no-meanings/no-translation,
  Unicode sentence/token selection, alternate entry saving, lazy compounds,
  editing invalidation, out-of-order responses, collection failures, session
  cancellation, rescan identity and visibility. Existing popup tests must retain
  their behavioral coverage when markup/names change.
- Service: existing API/dictionary/tokenization/persistence/security tests and
  Ruff checks in the pinned environment; no OCR/dictionary parser rewrite or
  dependency change planned. Use `.github/workflows/checks.yml` commands and
  require no unexplained skips.
- Native: Cargo formatting, tests and builds on macOS and Windows through current
  Checks; extend actual coordinate/work-area/session cases. Native manual tests
  are necessary for hit routing, focus, permissions and capture contamination.
- Release: follow [desktop-release.md](desktop-release.md) for a future approved
  version and bind acceptance to each new installer hash. This planning task does
  not request more v0.1.0 testing, change historical evidence or authorize an
  installer/public release.

## 8. Completion criteria and current handoff

The implemented redesign is ready for source review when reading works with the
secondary window closed; both explicit scan modes and Rescan capture the intended
pixels; all non-region input reaches the reader; orange/blue and review states
remain aligned; the popup opens sentence-first, supports word/kanji exploration
and explicit copying/saving; and existing offline learning/persistence works.
Collections/settings must retain their error states, attribution and model checks.

### Phase 1 implementation — approved for continuation

Implemented the semantic tokens and small control/focus primitives, a standalone
520 × 56 logical px toolbar (112 × 48 collapsed), drag/keyboard movement,
Selected Area/Whole Screen, fresh-pixel Rescan, reversible overlay visibility,
status/error/cancel controls, and access to existing collections/settings/notices
and Quit. Native window bounds follow content, including overflow/status rows.
The secondary main window starts hidden; closing it keeps the toolbar/service
alive. Global O selects an area; global S now scans the whole pointer monitor.
Toolbar buttons use its monitor; Rescan retains the original successful target.

The supporting native session rejects overlapping scans, stale completions and
changed monitor layouts. Capture hides utility windows and the native selector;
processing restores the toolbar without leaving a full-screen input blocker.
Whole Screen uses full physical monitor bounds, independent of selector/menu-bar
insets; selection and repeat captures reuse the existing coordinate/capture path.
Results and saved-data/service formats are preserved. The existing developer
capture preview remains available on recognition errors.
The native OCR window is reused on Rescan; each generation stays hidden until
its current polygons mount, avoiding window-label destruction races and old
geometry flashing at the new position. Failure retains the previous result.

The legacy main window's page/area controls and learning UI remain available in
this phase. Model import is accessed through Settings, using the existing verified
import UI. Full settings/library layout, overlay visuals/native hit routing,
region keyboard navigation and dictionary-popup refactoring are not implemented
or authorized by this phase. No new dependency/font/model, service behavior,
version number or release record was changed.

Verification and limits are recorded in the
[implementation status](implementation-plan.md#ui-redesign--phase-1-review).
The running macOS debug toolbar passed startup, collapse/expand, drag, menu,
secondary-window open/close/reopen and Quit smoke checks. The temporary debug
bundle has no Screen Recording grant; the existing permission failure is shown
in the toolbar and settings remain usable afterward. No OS permission was changed.
Successful native capture/Rescan/hide-show and Windows/mixed-monitor runtime
acceptance remain unverified; automated geometry/session/frontend tests cover
those source paths. These results are not installer acceptance.

### Planning verification retained

The original two-document planning deliverable passed Prettier and local link
checks, and the then-unchanged frontend baseline passed 100 tests in 18 files
and TypeScript. That historical planning pass does not certify redesigned UI.

### Phase 2 implementation — native acceptance gates open

The next approved slice implements `OCRBoundingBox` and scoped token-based region
styles, explicit uncertainty/demo labels, toolbar keyboard entry and a roving region
navigator. Native hit routing uses a polygon window region on Windows and native
cursor sampling/window ignore on macOS. It never runs OCR or lookup on hover and
retains browser/overlay drag ownership. Frame changes hide stale geometry; capture,
hide/show, generations and optional reading-order controls retain their guards.
The existing popup gains review guidance and keyboard dismissal/focus return only.
Its content/layout redesign remains the next phase; **Compact popup** is the latest
owner choice in the visual preview.

See [implementation status](implementation-plan.md#ui-redesign--phase-2-review)
and [native UI checks](ui-overlay-testing.md) for evidence and remaining gates.
Automated checks do not certify native input routing on both platforms. Do not
proceed to the popup phase or claim the full redesign accepted while those gates
remain open. No installer publication is authorized.

Next action: native Phase 2 checks and owner review before the dictionary popup phase.
