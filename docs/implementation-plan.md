# YomiMado — Implementation Plan

This document turns the initial design into incremental engineering milestones for Codex.

## Guiding rule

Build a small vertical slice first. Do not implement future features before the current phase is demonstrably working.

## Current status

Installer audit (2026-10-06): the approved hobby candidate passed browser
download hash/quarantine and Finder installation, but first launch reported
damaged because the linker-only signature lacks a bundle resource seal.
Packaging now requests a local ad-hoc seal and verifies it plus native signatures.
The replacement at clean commit `5120506` passes mounted bundle/signature/source
and frozen OCR/learning/persistence checks. Browser quarantine, Finder install,
per-app Open Anyway, model import/rejection/cancellation and restart pass.
Refreshing the old development Screen Recording entry allows the installed
app to open capture and return OCR regions. The maintainer confirms the global
shortcut and aligned synthetic vertical OCR on Retina. In-app credits and
screenshotted word/kanji lookup, cached translation and saved entries pass.
The maintainer confirms offline capture/lookup, the shortcut after reboot and
saved-data restart persistence. Explicit page scan, uncached translation and
test-entry removal pass with maintainer confirmation. The installed-app gate is
cleared for candidate `5120506`; fresh-Mac and other untested subcases stay
explicit in the release record. A CI rebuild needs a new installer confirmation.
Native licence/source review and maintainer approval remain complete.

Release policy (2026-10-06): versioned feature merges into `main` trigger the
macOS hobby release workflow. It builds the merged commit, preserves the
reviewed runtime/source inputs, verifies artifact transfers, and creates
`v<app version>` plus the public GitHub release after protected installer
confirmation. On 2026-10-07, release classification follows the version:
`0.x.x` and `alpha.N`/`beta.N`/`rc.N` suffixes are pre-releases; `1.0.0` and
later without a suffix are stable. Artifact provenance and GitHub's draft flag
must agree with that rule; both paths retain all release gates. Local
workflow/rebuild checks pass. The protected GitHub release
environment is configured and API-verified on 2026-10-07. The three reviewed
seed assets are saved in a private draft with matching uploaded hashes. `main`
is created at `cc8a95c` and set as GitHub's default branch; `develop` remains
unmerged as requested. Hosted execution and its new installer confirmation
are pending the first merge; no version tag or public release has been created.
See [the release setup](macos-release.md#release-on-merge-to-main).

Status audit (2026-10-05): the capture → local OCR → interactive overlay →
learning-popup flow works with user-installed models on macOS and has been
manually exercised on a Retina display. The desktop (55), Rust (36), and OCR
service (47) automated tests pass. These tests do not replace the remaining
Windows and left-of-primary alignment checks. Without user-local detector and
recognizer models, OCR returns a labeled demo boundary, not recognized text.
Translation is on-demand with a separately installed local model; missing-model
errors are shown rather than inventing a result.

| Phase            | Current state                                                                      | Main remaining work                                                                            |
| ---------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 0 — Bootstrap    | App, service, shared contract, GPL-3.0-only source license, and docs exist         | No required core task open                                                                     |
| 1 — Capture      | Implemented and manually tried on macOS Retina and two differently shaped monitors | Windows scaled-display manual test with a packaged pre-release build                           |
| 2 — OCR          | Local detector/recognizer and geometry work with installed models                  | Reproducible detector/model pins; OCR-quality limits below; no calibrated confidence available |
| 3 — Integration  | Capture-to-OCR client flow works                                                   | Request/result correlation IDs                                                                 |
| 4 — Overlay      | Interactive overlay and two-monitor layout tested on macOS                         | Windows scaling and left-of-primary alignment checks                                           |
| 5 — Tokenization | Selected-region tokenization works                                                 | No required core task open                                                                     |
| 6 — Dictionary   | Local word/kanji lookup works                                                      | Optional result cache; packaging/data updates                                                  |
| 7 — Translation  | Explicit local translation and SQLite cache work                                   | Surrounding-sentence context                                                                   |
| 8 — Kanji        | Select a kanji from a popup word                                                   | Direct on-page character hit boxes/crop fallback                                               |
| 9 — Learning     | Save, review, and remove words/sentences                                           | Anki export deferred; other learning extras                                                    |
| 10 — Page scan   | One-shot crop/filter/OCR and opt-in reading order work                             | Stronger filtering, panel order, SFX handling, incremental scans                               |

---

# Phase 0 — Repository bootstrap

## Goal

Create the smallest repository structure capable of building a Tauri desktop app plus a separate Python OCR service.

## Tasks

- [x] Initialize git repository.
- [x] Create Tauri 2 desktop app.
- [x] Create React + TypeScript frontend.
- [x] Create Rust native layer.
- [x] Create Python OCR service skeleton.
- [x] Create shared TypeScript domain types.
- [x] Choose and add the project `LICENSE` file (GPL-3.0-only).
- [x] Create `THIRD_PARTY_LICENSES/` with initial dependency notices (full release notices still pending).
- [x] Add basic README with project purpose and current status.
- [x] Add the initial design and implementation-plan docs.

## Done when

```text
Desktop app launches.
Python OCR service can start independently.
Frontend can reach the local service over HTTP; the service has a tested health endpoint.
```

Do not add actual OCR dependencies yet if doing so blocks basic project setup.

Status: the desktop and Python service are in place, the health endpoint is
tested, and the project source is licensed under GPL-3.0-only. Third-party
assets and packaged-release notices are tracked separately under release
hygiene.

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
- [x] manual test on one macOS Retina display
- [ ] manual test on Windows with non-100% display scaling (planned with a packaged pre-release build)

## Done when

A user can select the Japanese text shown in the supplied screenshots and save/capture an image that visually matches the selected screen region.

Status: the flow is implemented and the user has exercised it on macOS Retina.
The Windows non-100% scaling check is still open; Windows capture has not been
manually signed off for this milestone.

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
- [ ] Pin the detector checkout, model assets, and remaining Python runtime dependencies reproducibly (`manga-ocr` itself is pinned).
- [x] Implement image input adapter.
- [x] Implement text-region detection adapter.
- [x] Implement Manga OCR recognition adapter.
- [x] Show recognition confidence as unknown when Manga OCR provides no calibrated score; do not derive one from heuristics.
- [x] Preserve polygon/bounding-box geometry.
- [x] Detect or infer orientation.
- [ ] Add a `soundEffect`/dialogue/etc. field when feasible; do not block the milestone if type classification is not ready.
- [x] Implement `POST /api/v1/ocr` (real local OCR when models are configured; labeled demo response otherwise).
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
        { "x": 100, "y": 100 },
        { "x": 180, "y": 100 },
        { "x": 180, "y": 240 },
        { "x": 100, "y": 240 }
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

Status: real local OCR and geometry have been exercised on user-local manga
captures, including vertical text and transparent-bubble recovery. Detection
and recognition still miss some text. Manga OCR does not provide a calibrated
confidence value, so no numeric recognition-confidence feature is planned for
the current provider. The API uses zero as an unknown sentinel, while the UI
labels it "unknown" and uses review markers where geometry is approximate.
Text-type classification is not implemented, so regions currently use `other`.

---

# Phase 3 — Shared OCR contract + frontend integration

## Goal

Make the desktop application consume OCR results without knowing Python implementation details.

## Tasks

- [x] Define shared TypeScript types.
- [x] Implement a frontend OCR HTTP client boundary independent of Python internals.
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

Status: the capture selector sends image data to the local OCR client, parses
structured regions, and shows an overlay. Region IDs exist, but a separate
request/result correlation ID is not yet carried through the pipeline.

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
- [ ] Verify alignment across the full supported display-scaling matrix.
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

- [x] macOS Retina (user-tested)
- [ ] macOS non-Retina if available
- [ ] Windows 100% (planned with a packaged pre-release build)
- [ ] Windows 125% (planned with a packaged pre-release build)
- [ ] Windows 150% (planned with a packaged pre-release build)
- [x] two-monitor layout with different aspect ratios (user-tested on macOS)
- [ ] monitor placed to the left of primary display

## Done when

The user can see interactive OCR regions exactly over the Japanese text on the original screen, without visible drift at supported scaling configurations.

Status: interactive alignment has been exercised on macOS Retina and the user
tested two monitors with different aspect ratios. A scan targets the monitor
containing the main app window at scan start; this is the intended current
behavior. Windows and left-of-primary checks still need explicit manual
verification. Tests cover coordinate transforms but cannot prove physical-screen
alignment.

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
  translate(input: TranslateSentenceInput): Promise<TranslationResult>;
}
```

## Done when

A user can click a recognized sentence and explicitly request its translation.

Status: on-demand local translation, source preservation, caching, and error
display are implemented. The provider currently receives the selected text
only; surrounding OCR context is not sent, so translation is not guaranteed to
resolve ambiguous meaning from the page.

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
- [x] save sentence (explicit local save with optional requested translation)
- [x] review saved words in the main window and remove entries
- [x] review saved sentences in the main window and remove entries
- [ ] Anki export (deferred at the user's request)
- [ ] grammar explanation
- [ ] furigana overlay
- [ ] pitch-accent integration

These should be implemented only after the core capture/OCR/selection interaction is stable.

Status: words and sentences can be saved explicitly in the local SQLite
database. A sentence may include an English translation only after the reader
requests translation and saves again. The main window lists and removes saved
words and sentences separately. This is not spaced repetition, Anki export, or
automatic saving of OCR results.

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
When a clear light page edge is followed by a short dark site toolbar at the
bottom of the capture, the crop stops before that toolbar; ambiguous dark
content remains included to avoid cutting off a manga panel.
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
Page scans now arrange OCR regions into estimated horizontal bands, then read
right-to-left across each band and top-to-bottom within an overlapping text
column. Reading-order controls are disabled by default in the main-window
Reading settings. When enabled, the overlay shows a fixed navigation row with
the selected text below it, without a separate on-page toggle button.
Clicking any region still works. The preference is stored locally. This uses
text geometry only, so unusual panel layouts may be ordered incorrectly. Panel
detection and reliable page-wide reading-order reconstruction remain future work.

Current one-shot flow:

```text
scan display → auto-crop page or use saved area → OCR → overlay
```

Future incremental flow (not implemented):

```text
screen changes
     ↓
incremental detection
     ↓
update affected OCR regions
```

## Tasks

- [x] conservative automatic manga-region detection with saved-area fallback
- [x] basic text-region filtering with debug reasons
- [ ] stronger artwork-versus-text filtering without hiding uncertain dialogue
- [ ] panel ordering where useful
- [x] initial Japanese reading-order heuristic for page-scan navigation
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

- [x] pin the current Apple Silicon Python build environment and check it at
      build time; Cargo and npm already use tracked lockfiles
- [x] replace Xcode Python with source-built CPython 3.11.17 and static OpenSSL
      3.5.9/liblzma 5.8.4; preserve original sources, recipes and embedded notices
      in the isolated release runtime. Final source-delivery review remains open
- [x] audit the generated package inventory and add detector/bootloader plus
      native binary provenance; the former native FFmpeg GPL/LGPL notice mismatch
      is recorded in `docs/macos-source-review.md`
- [x] replace the OpenCV wheel with a source-pinned image/ONNX-only build;
      disable unused video dependencies and preserve its exact source/build notices
- [x] replace NumPy 1.26.4 with a source-pinned Accelerate build; remove
      its four OpenBLAS/GCC/libquadmath dylibs and preserve embedded notices
- [x] collect checksum-verified Rust/JavaScript and available Python source
      candidates; add the missing full libquadmath LGPL notice. Final source-delivery
      sign-off remains separate from completed native review.
- [x] complete native source/notice review for all 114 unique inputs; retain
      embedded notices, exact sources, build evidence and verified GEOS replacement
- [x] prepare the complete source delivery for human review: 75 archives/477
      entries, source-only asset omissions, unchanged retained-code/notice checks
      and offline locked Cargo resolution; defer app-size optimization until release
- [x] record source/licence approval by Git account chonnakanch on 2026-10-06
      for clean revision 042360e; verify the approved 477-entry source manifest and
      build instructions. Full filtered-source-only rebuild remains unverified;
      extracted project frontend/Rust and filtered Manga OCR checks pass.
- [x] verify bundled model-weight licensing and pin both weight checksums;
      require separate user installation for the detector ONNX file, whose
      redistribution terms are not explicit
- [x] verify EDRDG dictionary/data terms, bundle their licence, and document
      the monthly dictionary update procedure
- [x] update `THIRD_PARTY_LICENSES/` and make the macOS build generate a strict
      inventory of bundled software licences and upstream notice sources
- [x] build and smoke-test a private, self-contained Apple Silicon `.app` with
      the bundled OCR service, models, and dictionaries (health, OCR, JMdict,
      KANJIDIC2, Sudachi, and local translation)
- [x] rebuild and smoke-test an Apple Silicon `.app` that omits the detector
      ONNX weights and blocks scanning until setup
- [x] manually import the publisher's ONNX file in the packaged app and verify
      that a scan works afterward
- [x] build and inspect a private Apple Silicon DMG intended for direct
      download from GitHub Releases; its contained app passes strict asset/notice
      checks and local OCR, dictionary, kanji, tokenization, and translation smoke
      testing on the development Mac
- [x] choose a free unnotarized hobby DMG on 2026-10-05; Developer ID signing
      and Apple notarization are optional, with explicit per-app Gatekeeper steps
- [x] complete source/notice evidence for all 114 native inputs; source-build
      minimal Pillow/torchvision and OpenMP, remove training-only tools and
      compiled Tomli, and retain all embedded notices
- [x] build and verify the source-approved hobby candidate from clean revision
      042360e; exact mounted DMG/bundle and frozen-service smoke checks pass
- [x] finish installed-app testing for the sealed `5120506` candidate on the
      existing Mac, including maintainer-confirmed page scan, fresh translation,
      offline capture/lookup, reboot shortcut and saved-data persistence/removal
- Fresh-macOS install testing was skipped at the maintainer's request on
  2026-10-05 because no clean Mac is available; disclose this unverified case.
  Exact-DMG verification, model import and Screen Recording tests remain required.
- [ ] link the exact corresponding source revision and full notices alongside
      the public GitHub Release
- [x] add the main-triggered versioned GitHub Actions build after the hobby
      installer is releasable; never upload private outputs or detector weights
- [x] support stable releases from `1.0.0` onward without suffixes; keep `0.x.x`
      and alpha/beta/rc versions as pre-releases with verified classification
- [x] configure/API-verify the protected release environment with a required
      reviewer and main-only branch policy, without administrator bypass
- [x] save the reviewed GitHub seed assets as a private draft and verify hashes;
      create `main` at `cc8a95c`, set it as default and leave `develop` unmerged
- [ ] merge the release change into `main`, verify the hosted build, and confirm
      the exact new CI installer before approving public publication
- [x] keep copyrighted manga fixtures out of git (current tracked test assets)
- [x] document local model/data setup behavior
- [x] document macOS permissions
- [ ] document Windows installation/runtime requirements

# After the first release — UI redesign discussion

- [ ] Review the released app's main window, capture flow, OCR overlay, and learning popups with the user.
- [ ] Agree on the redesign goals and visual direction before creating mockups or changing the UI.
- [ ] Discuss a Jisho-inspired learning-popup layout: prominent word and reading,
      clearly grouped meanings, and compact kanji details (meanings and on/kun
      readings). Use it as visual inspiration, not a pixel-for-pixel copy.
- [ ] Keep the popup usable on smaller screens with stacked sections and
      scrolling. Do not include a Wikipedia section.
- [ ] Consider supplementary tags such as common-word status and JLPT level
      only where YomiMado has a suitable, attributed data source; do not invent
      levels or make them a prerequisite for the layout redesign.

This is a post-v1 discussion, not a requirement for the first release. Keep the
current UI stable while finishing and validating v1; do not assume a design or
implement a redesign until that discussion happens.
