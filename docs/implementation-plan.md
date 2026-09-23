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
- [x] Return image bytes/path to the OCR service.
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

- [ ] Integrate Sudachi implementation.
- [ ] Pin exact software and dictionary versions.
- [ ] Define tokenizer interface.
- [ ] Map token offsets back to original OCR strings.
- [ ] Produce surface form, reading, dictionary form, part of speech.
- [ ] Handle punctuation and unknown tokens.

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

---

# Phase 6 — Local dictionary lookup

## Goal

Provide instant offline word and kanji information.

## Tasks

- [ ] Import JMdict data into an application-friendly local format.
- [ ] Import KANJIDIC2 data.
- [ ] Add database/version metadata.
- [ ] Build indexes for expression and reading.
- [ ] Implement word lookup API.
- [ ] Implement kanji lookup API.
- [ ] Add dictionary result caching if useful.
- [ ] Add attribution/license metadata.

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

---

# Phase 7 — Sentence translation

## Goal

Translate only when the user explicitly asks.

## Tasks

- [ ] Define `TranslationProvider` interface.
- [ ] Add one configurable provider.
- [ ] Add sentence popup.
- [ ] Send Japanese text and optional immediate context.
- [ ] Preserve source Japanese.
- [ ] Cache translation results in SQLite.
- [ ] Show provider/API errors clearly.
- [ ] Never automatically translate all OCR regions.

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
- [ ] Lookup KANJIDIC2.
- [ ] Show on-yomi/kun-yomi and meanings.
- [ ] Show selected example compounds.

## Done when

The user can select an individual kanji from recognized text and receive useful local information.

---

# Phase 9 — Learning features

## Candidates

- [ ] vocabulary history
- [ ] save word
- [ ] save sentence
- [ ] review history
- [ ] Anki export
- [ ] grammar explanation
- [ ] furigana overlay
- [ ] pitch-accent integration

These should be implemented only after the core capture/OCR/selection interaction is stable.

---

# Phase 10 — Automatic page detection

## Goal

Reduce manual capture work.

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

- [ ] automatic manga-region detection
- [ ] text-region filtering
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
