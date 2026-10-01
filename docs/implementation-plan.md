# YomiMado — Implementation Plan

This document turns the initial design into incremental engineering milestones for Codex.

## Guiding rule

Build a small vertical slice first. Do not implement future features before the current phase is demonstrably working.

## Current status

The desktop and OCR service build and pass automated tests. The capture flow,
coordinate transform, and transparent overlay still need manual validation on
macOS Retina and scaled Windows displays. Without user-local detector and
recognizer models, the OCR service returns a labeled demo boundary for the
selected area. Phase 1 and Phase 2 are not complete until their respective
"Done when" criteria below are verified with actual captures and real OCR.

At the user's request, an on-demand local translation slice is being added
before those manual OCR/overlay checks are complete. This does not mark the
earlier phases complete. Translation requires a separately installed local
model; the no-model path shows a setup error rather than inventing a result.

---

# Phase 0 — Repository bootstrap
  
## Goal

Create the smallest repository structure capable of building a Tauri desktop app plus a separate Python OCR service.

## Tasks

- [ ] Initialize git repository if needed.
- [x] Create Tauri 2 desktop app.
- [x] Create React + TypeScript frontend.
- [x] Create Rust native layer.
- [x] Create Python OCR service skeleton.
- [x] Create shared TypeScript domain types.
- [ ] Add project license and third-party license directory.
- [x] Add basic README with project purpose and current status.
- [ ] Add docs from this design package.

## Done when

```text
Desktop app launches.
Python OCR service can start independently.
Frontend can call a trivial health endpoint.
```

Do not add actual OCR dependencies yet if doing so blocks basic project setup.

---

# Phase 1 — Screen capture

## Goal

Capture a user-selected screen region on Windows and macOS.

## UX

```text
Run app
  ↓
Cmd/Ctrl + Shift + O
  ↓
screen selection overlay
  ↓
user drags rectangle
  ↓
image captured
```

## Tasks

- [x] Add global shortcut support.
- [x] Create capture-selection window.
- [x] Enumerate displays/monitors.
- [x] Capture selected rectangle.
- [x] Return image bytes to the OCR service.
- [x] Keep captures in memory and remove legacy cached PNG captures on app startup.
- [x] Record capture metadata:
  - [x] monitor identifier
  - [x] physical image width/height
  - [x] logical bounds where available
  - [x] selection origin
  - [x] scale factor
- [x] Handle macOS screen-recording permission failure gracefully.
- [x] Handle Windows capture failure gracefully.

## Tests

- [x] unit tests for rectangle normalization
- [x] unit tests for negative monitor origins
- [x] tests for 1x / 2x scale conversions
- [ ] manual test on one macOS Retina display
- [ ] manual test on Windows with non-100% display scaling

## Done when

A user can select the Japanese text shown in the supplied screenshots and save/capture an image that visually matches the selected screen region.

---

# Phase 2 — OCR service

## Goal

Run local manga text detection and Manga OCR against a captured image and return structured geometry.

## Pipeline

```text
image
 ↓
preprocess
 ↓
text detector
 ↓
regions
 ↓
Manga OCR
 ↓
recognized Japanese
```

## Tasks

- [x] Add a local comic-text-detector adapter (model and checkout are user-supplied).
- [x] Add optional Manga OCR dependency (model is user-supplied).
- [ ] Pin Python/model dependency versions.
- [x] Implement image input adapter.
- [x] Implement text-region detection adapter.
- [x] Implement Manga OCR recognition adapter.
- [ ] Add recognition confidence where available.
- [x] Preserve polygon/bounding-box geometry.
- [x] Detect or infer orientation.
- [ ] Add a `soundEffect`/dialogue/etc. field when feasible; do not block the milestone if type classification is not ready.
- [x] Implement `POST /api/v1/ocr` (structured placeholder until OCR dependencies are selected).
- [x] Add `/health` endpoint.
- [x] Add structured error responses.
- [x] Add opt-in detector-box/crop diagnostics for local OCR debugging.
- [x] Retry small, partially detected selections with whole-crop Manga OCR; mark fallback geometry as approximate.
- [x] Recover plausible whole-crop text from small selections with no detector boxes; retain approximate geometry and unknown confidence.
- [x] Retry medium and larger captures on bounded overlapping detector tiles and merge nonduplicate boxes in image coordinates.

## Suggested service structure

```text
services/ocr/
├── app/
│   ├── api/
│   │   ├── health.py
│   │   └── ocr.py
│   ├── detector/
│   │   └── detector.py
│   ├── recognition/
│   │   └── manga_ocr.py
│   ├── pipeline/
│   │   └── pipeline.py
│   └── main.py
└── tests/
```

Keep this conceptual structure small; do not split classes/modules just for symmetry.

## API shape

```http
POST /api/v1/ocr
Content-Type: multipart/form-data
```

Response:

```json
{
  "regions": [
    {
      "id": "region-1",
      "text": "学校",
      "polygon": [
        {"x": 100, "y": 100},
        {"x": 180, "y": 100},
        {"x": 180, "y": 240},
        {"x": 100, "y": 240}
      ],
      "orientation": "vertical",
      "confidence": 0.95,
      "type": "dialogue",
      "tokens": []
    }
  ]
}
```

## Test fixtures

Do not put commercial manga pages into git.

Use:

- synthetic manga-like images
- publicly licensed images
- local developer fixtures ignored by git

The two screenshots supplied during design should be treated as private/manual validation inputs unless their redistribution rights are verified.

## Done when

The OCR service can accept a captured image and return structured Japanese text regions with reliable coordinates for representative manga input.

---

# Phase 3 — Shared OCR contract + frontend integration

## Goal

Make the desktop application consume OCR results without knowing Python implementation details.

## Tasks

- [x] Define shared TypeScript types.
- [ ] Implement Rust/API client boundary.
- [x] Send captured image to local OCR service.
- [x] Parse OCR response.
- [x] Show processing state.
- [x] Handle OCR timeout/error.
- [ ] Preserve OCR request/result identifiers for debugging.

## Done when

The desktop app can perform:

```text
hotkey → capture → OCR → structured frontend result
```

without hardcoded test JSON.

---

# Phase 4 — Transparent OCR overlay

## Goal

Draw OCR regions over the original manga with correct alignment.

## Tasks

- [x] Create transparent overlay window.
- [x] Make overlay always-on-top when active.
- [x] Map OCR image coordinates to overlay coordinates.
- [x] Render region outlines/highlights.
- [x] Render hover/active state.
- [x] Make region clickable.
- [x] Dismiss overlay cleanly.
- [ ] Verify alignment across display scaling configurations.
- [x] Support vertical text regions.

The OCR overlay retrieves its region data from native in-memory state. Only
the overlay mode is placed in the webview URL, so text-heavy page scans do not
exceed development-server request-header limits.

## Coordinate model

```text
screen physical pixels
        ↓
capture origin + scale
        ↓
OCR pixels
        ↓
overlay logical pixels
```

Do not put coordinate math directly into UI components. Create one transformation utility/module and test it heavily.

## Required manual tests

- [ ] macOS Retina
- [ ] macOS non-Retina if available
- [ ] Windows 100%
- [ ] Windows 125%
- [ ] Windows 150%
- [ ] two-monitor layout
- [ ] monitor placed to the left of primary display

## Done when

The user can see interactive OCR regions exactly over the Japanese text on the original screen, without visible drift at supported scaling configurations.

---

# Phase 5 — Japanese tokenization

## Goal

Turn OCR strings into useful Japanese tokens/readings.

## Tasks

- [x] Integrate Sudachi implementation.
- [x] Pin exact software and dictionary versions.
- [x] Define tokenizer interface.
- [x] Map token offsets back to original OCR strings.
- [x] Produce surface form, reading, dictionary form, part of speech.
- [x] Handle punctuation and unknown tokens.

## Example

Input:

```text
今日は学校に行きたくない。
```

Expected conceptual output:

```text
今日 / は / 学校 / に / 行き / たく / ない / 。
```

Exact segmentation can differ depending on dictionary mode/version; use the selected tokenizer's actual output rather than hardcoding this example.

## Done when

A selected OCR region can be displayed as structured Japanese tokens.

Status: complete for the selected-region popup. Analysis is on-demand through
`POST /api/v1/tokenize`; the OCR response's `tokens` array is still empty, so
full-screen detection does not tokenize every region unnecessarily. The popup
shows details only for a word the user selects in its OCR text; punctuation is
kept in the source sentence but omitted as a study token. Direct word selection
on the manga image still needs finer character geometry. User-installed JMdict
and KANJIDIC2 files now support whole-word and individual-kanji lookup from
the selected word.

---

# Phase 6 — Local dictionary lookup

## Goal

Provide instant offline word and kanji information.

## Tasks

- [x] Index user-installed JMdict XML/XML.gz in a local SQLite lookup file.
- [x] Read user-installed KANJIDIC2 XML/XML.gz data locally (not bundled).
- [x] Record source fingerprint and index schema version for automatic rebuilds.
- [x] Build a lookup index for JMdict written expressions and readings.
- [x] Implement word lookup API.
- [x] Implement single-character kanji lookup API.
- [ ] Add dictionary result caching if useful.
- [x] Add KANJIDIC2 attribution/license metadata in UI and docs.
- [x] Add JMdict attribution/license metadata in UI and docs.

## UI

Click:

```text
学校
```

Show:

```text
学校
がっこう
school
```

## Done when

Word selection shows useful local dictionary information without a network request.

Status: core word and character lookup work with user-installed JMdict and
KANJIDIC2 files. JMdict can return multiple possible senses; the app does not
disambiguate them using sentence context. A clicked kanji also shows short
example compounds from JMdict, preferring common entries. Packaging and data
update automation are not implemented yet.

---

# Phase 7 — Sentence translation

## Goal

Translate only when the user explicitly asks.

## Tasks

- [x] Define `TranslationProvider` interface.
- [x] Add one configurable local provider (model path is user-supplied).
- [x] Add sentence popup.
- [ ] Send Japanese text and optional immediate context.
- [x] Preserve source Japanese.
- [x] Cache translation results in SQLite.
- [x] Show provider/API errors clearly.
- [x] Never automatically translate all OCR regions.

## Conceptual interface

```typescript
interface TranslationProvider {
  translate(input: TranslateSentenceInput): Promise<TranslationResult>
}
```

## Done when

A user can click a recognized sentence and explicitly request a contextual translation.

---

# Phase 8 — Kanji-level interaction

## Goal

Allow individual kanji learning.

## First approach

Click a word, then choose a character.

```text
学校
 ↑
```

## Later approach

Each character gets an independent hit box.

## Tasks

- [ ] Add per-character or approximate character geometry.
- [ ] Add fallback click-crop OCR where useful.
- [x] Lookup user-installed KANJIDIC2 from a selected popup word.
- [x] Show on-yomi/kun-yomi and meanings in the popup.
- [x] Show selected example compounds from user-installed JMdict.

Status: the first approach works with local dictionary data. Direct clicks on
characters in the manga image still need finer OCR geometry. Compound examples
are dictionary words, not example sentences or context-specific readings.

## Done when

The user can select an individual kanji from recognized text and receive useful local information.

---

# Phase 9 — Learning features

## Candidates

- [x] vocabulary history (explicitly saved words in local SQLite)
- [x] save word (chosen JMdict entry and source sentence)
- [ ] save sentence
- [x] review saved words in the main window and remove entries
- [ ] Anki export
- [ ] grammar explanation
- [ ] furigana overlay
- [ ] pitch-accent integration

These should be implemented only after the core capture/OCR/selection interaction is stable.

Status: the first learning-history slice is available. Saving is an explicit
action on a selected dictionary entry, and the main window lists/removes saved
words. This is not spaced repetition, Anki export, or automatic saving of OCR
results.

---

# Phase 10 — Automatic page detection

## Goal

Reduce manual capture work.

Status: a one-shot **Scan manga page** action attempts a conservative
black-and-white page crop beneath darker browser controls before OCR. If the
image is ambiguous it uses the saved manga area or asks the reader to draw one.
The crop looks for one contiguous page-like span, excluding sparse white text
and thumbnails in a dark website sidebar; similarly sized competing spans
still fall back to the saved area. The page evidence threshold accepts fine
line art with relatively little solid-black ink, as verified against local
Comipo and X screenshots without adding those images to the repository.
**Set/adjust scan area** redraws the fallback, and Cmd/Ctrl+Shift+S starts the
same scan. The saved area is keyed to display bounds and scale. This first-pass
page detection deliberately declines light-themed or unusual layouts, and it
does not eliminate false OCR within a page. It is not continuous scanning.

An initial text-region filter rejects nearly uniform detector crops and OCR
strings with no Japanese script. Capture debug retains those raw boxes, crops,
recognized strings, and explicit rejection reasons. This is deliberately not
a confidence filter: Manga OCR does not supply a calibrated confidence score.
Japanese-looking OCR hallucinations in artwork remain possible.
Medium and larger captures now get a bounded overlapping-tile detector retry.
When the detector's text mask identifies aligned short glyphs that its box
grouping omits, a text-mask retry offers those local boxes to Manga OCR. This
does not add a second model inference pass. Recognition uses the original
pixels, and retry boxes preserve full-image coordinates. Capture debug labels
tile and text-mask candidates. Transparent-bubble text may still be missed;
mask candidates are filtered but do not have calibrated confidence.
The short `みて` text in a user-local transparent-bubble screenshot was
recovered through this mask path with the installed detector and Manga OCR
models; that copyrighted screenshot is not part of the repository.
Text-mask-only matches are now kept clickable but marked with a dashed gold
review outline in Capture debug and the OCR overlay. Capture debug explains
why each candidate was kept or filtered. This is an evidence label, not a
calibrated confidence score; stronger artwork-versus-text discrimination still
needs more representative local validation before it can safely reject
Japanese-looking candidates.
The text-mask fallback also accepts aligned small kana between larger vertical
glyphs, so short words are less likely to split when rendered at different
display scales. It remains a review-suggested fallback, not a confidence score.
A longer aligned mask recognition may supersede a one-character detector result
instead of being discarded as a duplicate; the debug view records that decision.
When a larger automatic crop leaves a one- or two-character vertical fragment,
OCR now makes up to six bounded recognizer-only retries on taller crops of the
original pixels. Tall boxes mislabeled horizontal are eligible too. A longer
result is shown with approximate geometry and a review marker; rejected or
failed retries leave the original detector result unchanged. This does not run
another detector pass or alter the existing tile budget.

Current manual flow:

```text
select area → OCR
```

Future flow:

```text
screen capture
     ↓
automatic text detection
     ↓
OCR all relevant regions
```

## Tasks

- [x] conservative automatic manga-region detection with saved-area fallback
- [x] basic text-region filtering with debug reasons
- [ ] stronger artwork-versus-text filtering without hiding uncertain dialogue
- [ ] panel ordering where useful
- [ ] Japanese reading-order heuristics
- [ ] sound-effect filtering
- [ ] incremental updates when the screen changes

This phase is intentionally later because it increases complexity significantly.

---

# Milestone priority

The critical path is:

```text
Phase 0
  ↓
Phase 1  Screen Capture
  ↓
Phase 2  OCR
  ↓
Phase 3  Integration
  ↓
Phase 4  Overlay
  ↓
Phase 5  Tokenization
  ↓
Phase 6  Dictionary
  ↓
Phase 7  Translation
  ↓
Phase 8  Kanji
```

Do not skip directly to translation before OCR geometry and overlay are reliable.

# First Codex task

The first implementation task should be:

> Inspect the repository. Read `AGENTS.md`, `docs/initial-design.md`, and this file. Implement Phase 0 and Phase 1 only. Build the smallest Tauri 2 + React + TypeScript desktop app with a Rust screen-capture/global-shortcut layer and a minimal Python OCR-service skeleton. Implement the user-selected region capture flow on macOS and Windows, preserving enough coordinate/scale metadata to support the later overlay. Add focused tests for rectangle normalization and coordinate transforms. Do not implement dictionary, translation, tokenization, automatic OCR, or learning UI yet.

Codex should inspect the current repository before creating files and should adapt this plan to what already exists rather than blindly generating the entire target tree.

# Definition of MVP completion

YomiMado MVP is considered technically proven when:

```text
Browser/manga viewer
      ↓
Cmd/Ctrl+Shift+O
      ↓
select region
      ↓
local OCR
      ↓
Japanese text regions
      ↓
transparent aligned overlay
      ↓
click a region
```

At that point, the architecture has been validated and the Japanese-learning layers can be developed independently.

# Release hygiene

Before any public release:

- [ ] verify dependency versions and licenses
- [ ] verify model weights/licenses
- [ ] verify dictionary/data licenses
- [ ] update `THIRD_PARTY_LICENSES/`
- [ ] avoid copyrighted manga fixtures in git
- [ ] document local model/data download behavior
- [ ] document macOS permissions
- [ ] document Windows installation/runtime requirements
