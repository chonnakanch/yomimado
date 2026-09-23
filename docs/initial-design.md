# YomiMado — Initial Product and Technical Design

## 1. Product overview

**YomiMado (読み窓)** is a cross-platform desktop Japanese manga reading assistant for **Windows and macOS**.

The primary use case is reading untranslated Japanese manga that is already visible on the user's screen, including manga viewed in a web browser or image/PDF reader.

The application is intended primarily for **Japanese language learning**.

The core idea is not to replace Japanese with English. Instead, YomiMado adds an interactive learning layer over the original Japanese:

```text
Japanese manga on screen
        ↓
       OCR
        ↓
 interactive Japanese
        ↓
 ┌──────┼─────────┐
 ↓      ↓         ↓
word  sentence   kanji
 ↓      ↓         ↓
reading translation reading/meaning
```

Working tagline:

> **Read beyond the page.**

The product name is a working name and has not been trademark/domain/package-name cleared.

## 2. Inspiration and references

The project was motivated by the capabilities demonstrated by:

- [Cloe](https://github.com/blueaxis/Cloe) — desktop OCR workflow/reference.
- [Mokuro](https://github.com/kha-white/mokuro) — selectable manga text and HTML-overlay approach.
- [Manga OCR](https://github.com/kha-white/manga-ocr) — Japanese manga OCR model/software.
- [Yomeru](https://yomeru.ai/en) — Japanese-learning-oriented interaction model.

The intent is to build a distinct screen-overlay learning application rather than reproduce any reference project's UI wholesale.

Manga OCR's current repository describes support for vertical and horizontal Japanese, furigana, text over images, varied fonts, low-quality images, and multi-line text. Mokuro is a useful architectural reference because it combines manga OCR with selectable overlays. comic-text-detector is designed to extract manga/comic text regions and geometry. citeturn106493search0turn106493search2turn106493search1

## 3. Real-world input assumptions

Two representative screenshots were provided during design:

### Screenshot A — realistic manga page

Characteristics observed:

- mostly vertical Japanese dialogue
- multiple manga panels on one screen
- several speech bubbles
- small speech-bubble text mixed with artwork
- stylized sound effects
- different font sizes
- text close to illustration boundaries
- multiple independent text regions
- a need for reading-order awareness eventually

This represents the difficult end of the OCR problem.

### Screenshot B — clean illustrated example

Characteristics observed:

- relatively clean, high-contrast line art
- large Japanese speech text
- vertical text
- a straightforward dialogue bubble
- useful as an easy OCR/overlay test case

These screenshots demonstrate that the system must support geometry, vertical text, and independent text regions from the beginning.

## 4. User experience

### 4.1 Primary workflow

```text
User is reading manga in browser/PDF/image viewer
                     ↓
            presses Cmd/Ctrl+Shift+O
                     ↓
              selects a region
                     ↓
              screenshot captured
                     ↓
                 local OCR
                     ↓
           OCR results appear as overlay
                     ↓
                user clicks text
                     ↓
              learning information
```

The first implementation should not automatically OCR the entire screen continuously.

### 4.2 Word interaction

Example:

```text
学校に行く
```

Clicking a recognized word should eventually show:

```text
学校
がっこう
school
```

Where possible, also show:

- dictionary form
- part of speech
- additional definitions
- example compounds

### 4.3 Sentence interaction

Example:

```text
今日は学校に行きたくない。
```

The user can request contextual translation. The popup should retain the original Japanese and may show word/grammar information alongside the translation.

Example conceptual UI:

```text
┌─────────────────────────────────┐
│ 今日は学校に行きたくない。       │
│                                 │
│ 今日        きょう              │
│ 学校        がっこう            │
│ 行く        いく                │
│                                 │
│ Translation                     │
│ I don't want to go to school    │
│ today.                          │
│                                 │
│ Grammar                         │
│ 行く → 行きたい → 行きたくない  │
└─────────────────────────────────┘
```

The example translation above is illustrative only.

### 4.4 Kanji interaction

Eventually the user should be able to click an individual character inside a recognized word/sentence.

Example:

```text
学
```

Popup:

```text
学

音読み
ガク

訓読み
まなぶ

Meanings
study / learning
```

The exact kanji content should come from local dictionary data, not an LLM by default.

## 5. Product principles

### 5.1 Capture, don't replace

The source manga remains visible and unchanged.

YomiMado adds:

- text-region highlights
- selectable words
- readings
- dictionary information
- contextual translation
- learning popups

The initial product is not an image translation/inpainting application.

### 5.2 Local-first

The default processing pipeline should be:

```text
Screen image
   ↓
local detection
   ↓
local OCR
   ↓
local Japanese analysis
   ↓
local dictionary
```

Network access should be limited to explicitly requested functionality such as translation.

### 5.3 Geometry-first OCR model

Never represent OCR as only:

```json
{"text": "学校"}
```

The application needs geometry:

```json
{
  "text": "学校",
  "polygon": [
    {"x": 100, "y": 200},
    {"x": 180, "y": 200},
    {"x": 180, "y": 340},
    {"x": 100, "y": 340}
  ],
  "orientation": "vertical"
}
```

This is what enables overlay positioning and later word/character hit-testing.

## 6. Technical architecture

```text
┌───────────────────────────────────────────────────────┐
│                    Desktop App                        │
│                 Tauri 2 + React                       │
│                                                       │
│  React/TypeScript                                     │
│  ├── Main/settings                                    │
│  ├── Capture selector                                 │
│  ├── OCR overlay                                      │
│  ├── Dictionary popup                                 │
│  └── Translation/learning popup                      │
│                                                       │
│  Rust/Tauri                                           │
│  ├── Global shortcut                                  │
│  ├── Screen capture                                  │
│  ├── Window management                                │
│  └── OCR process lifecycle                            │
└─────────────────────────┬─────────────────────────────┘
                          │ local HTTP / IPC
                          ▼
┌───────────────────────────────────────────────────────┐
│                    OCR Service                         │
│                     Python                            │
│                                                       │
│  screenshot                                             │
│      ↓                                                │
│  text detection                                       │
│      ↓                                                │
│  Manga OCR                                            │
│      ↓                                                │
│  text normalization                                   │
│      ↓                                                │
│  Japanese tokenizer                                   │
└─────────────────────────┬─────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────┐
│                   Local Data                          │
│                                                       │
│  JMdict / KANJIDIC2 / tokenizer data                 │
│  SQLite cache + vocabulary/history                    │
└─────────────────────────┬─────────────────────────────┘
                          │
                          │ user requested only
                          ▼
                    Translation API
```

### Desktop shell

Tauri 2 is the selected desktop framework. Tauri's global shortcut plugin supports Windows and macOS, matching the initial platform scope. citeturn106493search4

### Screen capture

Start with a Rust capture abstraction backed by a cross-platform capture library such as xcap. Keep it behind the application's own interface so platform-native capture can be introduced later if required.

The implementation must account for permission and scaling differences between macOS and Windows.

### OCR service

Initially separate the Python OCR engine from the Tauri frontend/native layer. A localhost HTTP API is acceptable for the development architecture.

This keeps Python/model dependencies isolated and makes the OCR engine replaceable.

## 7. OCR pipeline

```text
Captured image
     ↓
preprocessing
     ↓
comic-text-detector
     ↓
text regions / lines / polygons
     ↓
region crops
     ↓
Manga OCR
     ↓
recognized Japanese text
     ↓
normalization
     ↓
Japanese morphological analysis
     ↓
structured TextRegion[]
```

Manga OCR supports vertical and horizontal text, furigana, text over images, varied fonts, low-quality images, and multiline text. comic-text-detector provides manga/comic text-region geometry. citeturn106493search0turn106493search1

## 8. Japanese analysis

The recognized Japanese should be analyzed into tokens.

Example:

```text
今日は学校に行きたくない。
```

Conceptual analysis:

```text
今日 | は | 学校 | に | 行き | たく | ない | 。
```

Use Sudachi behind an internal application interface.

The Sudachi organization currently identifies `sudachi.rs` as a Rust implementation/new-generation direction for Sudachi. Its README warns that its current 0.7 series is unstable and that exact versions/system dictionaries need careful pinning. Therefore, pin exact versions and keep dictionary compatibility explicit in the build. citeturn106493search7turn106493search8

## 9. Dictionary architecture

### JMdict

Use for word-level information:

```text
expression
reading
meanings
grammatical information
```

### KANJIDIC2

Use for individual kanji information:

```text
character
on-readings
kun-readings
meanings
selected metadata
```

Dictionary data is local so ordinary lookup is offline and fast.

## 10. Text types

Every OCR region should carry a type when possible:

```typescript
type TextRegionType =
  | 'dialogue'
  | 'narration'
  | 'soundEffect'
  | 'other'
```

This matters because manga pages contain sound effects and decorative text that should not always receive the same learning UI.

An initial detector/classifier does not need to be perfect. It can be optional metadata and a user-facing filter can be added later.

## 11. Coordinate system

Coordinate correctness is a core subsystem.

```text
physical screen pixels
        ↓
capture image pixels
        ↓
OCR coordinates
        ↓
overlay logical coordinates
        ↓
mouse coordinates
```

Never scatter scaling calculations throughout React/Rust.

Create one explicit transform layer with unit tests for:

- 1.0x scaling
- Retina 2.0x
- Windows 125%
- Windows 150%
- offsets for a non-zero monitor origin
- multiple displays
- scrolling/browser zoom scenarios where relevant

## 12. Overlay architecture

Use separate conceptual windows:

1. Main window — settings, history, vocabulary.
2. Capture window — region selection.
3. Overlay window — transparent OCR interaction.

The OCR overlay should render only learning/interaction elements and not a second copy of the manga.

The ideal interaction model is approximately:

```text
                 manga underneath

         ┌─────────────────────────┐
         │       OCR region        │
         │          学校           │
         └─────────────────────────┘
                    ↑
               hover/click
                    ↓
              learning popup
```

## 13. Word and character hit-testing

Do this incrementally.

### First implementation

Make a whole OCR region selectable.

### Next

Map tokens onto a region's geometry so the user can click a word.

### Later

Support per-character hit boxes for kanji selection.

A practical fallback for difficult character-level geometry is local re-OCR of a small crop around the user's click rather than requiring perfect character segmentation for the entire page.

## 14. Translation architecture

Define a provider abstraction:

```text
TranslationProvider
├── cloud provider A
├── cloud provider B
└── future local provider
```

Input should be structured, for example:

```typescript
interface TranslateSentenceInput {
  text: string
  previousText?: string
  nextText?: string
}
```

Translation should be performed only after an explicit user action.

Cache repeated translations in SQLite.

## 15. Performance goals

These are engineering targets for the prototype, not contractual guarantees:

| Stage | Target |
|---|---:|
| Capture | < 100 ms where practical |
| Detection | ~1–2 s |
| OCR | ~1–3 s |
| Tokenization | < 100 ms |
| Local dictionary lookup | < 20 ms |

The UI should show incremental progress rather than freezing the entire application.

## 16. Security/privacy model

Default behavior:

- screenshot stays local for OCR
- OCR is local
- dictionary lookup is local
- no automatic cloud upload
- translation API receives only requested text/context

Avoid logging raw screenshots or full OCR payloads by default.

## 17. Licensing approach

The project is intended to be open source and for personal use.

The implementation can use open-source dependencies according to their licenses; separate permission from project authors is not normally required when the license grants the relevant rights.

However, each dependency and asset must be reviewed individually.

Reference licenses discussed during design:

| Component | Current repository information | Notes |
|---|---|---|
| Manga OCR | Apache-2.0 | Software and model/data terms must both be checked before redistribution |
| comic-text-detector | GPL-3.0 | Distribution/derivative-work obligations apply to GPL-covered code |
| Cloe | GPL-3.0 | Reference app; prefer using as reference unless code is actually needed |
| Mokuro | GPL-3.0 | Reference app; not required wholesale |
| sudachi.rs | Apache-2.0 | Pin exact version; dictionary resources are separate |

Verify licenses again before each public release. The repository/license status can change over time.

Do not assume model weights, dictionaries, fonts, datasets, or generated assets share the software repository's license.

## 18. Copyright/content policy for the repository

Do not commit commercial manga screenshots or scraped DLsite content to the public repository.

For tests:

- use synthetic images
- use public-domain/licensed manga images
- or keep personal fixtures outside version control

The application is designed to process content already accessible to the user on their device; it should not need a server that downloads/stores manga content.

## 19. Deliberately out of scope for initial release

- mobile
- browser extension
- automatic continuous OCR
- manga translation/inpainting
- cloud OCR
- server-side manga storage
- account system
- cloud sync
- automatic full-page reading-order reconstruction
- advanced Anki workflow
- pitch-accent features

These can be reconsidered after the basic interaction works.

## 20. MVP definition

### v0.1 — OCR prototype

Must be able to:

1. launch the app
2. press global hotkey
3. select a screen region
4. capture the region
5. run local manga OCR
6. return Japanese text regions with geometry
7. render those regions on a transparent overlay aligned with the source screen
8. allow the user to select an OCR region

### v0.2 — Dictionary

Add:

- Japanese tokenization
- word selection
- JMdict lookup
- readings
- dictionary-form display

### v0.3 — Translation

Add:

- sentence selection
- contextual translation
- translation cache

### v0.4 — Kanji learning

Add:

- per-character hit testing
- KANJIDIC2 lookup
- kanji readings/meanings

### Later

- furigana overlay
- grammar explanations
- vocabulary history
- Anki export
- automatic detection
- reading order improvements
- study analytics

## 21. Success criteria

The project has demonstrated its core concept when a user can open a Japanese manga page like the supplied examples, trigger a capture, receive usable Japanese OCR locally, and click the detected text without losing alignment with the underlying manga.

The first success criterion is therefore **OCR geometry + overlay correctness**, not translation quality.
