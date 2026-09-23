# YomiMado — Codex Instructions

## Project identity

**Name:** YomiMado (読み窓)

YomiMado is an open-source desktop Japanese manga reading assistant for macOS and Windows. It reads Japanese text already visible on the user's screen, overlays interactive OCR regions, and provides Japanese-learning information such as readings, dictionary meanings, sentence translation, and individual kanji information.

Working tagline:

> Read beyond the page.

The name is a working product name and has not been trademark/domain/package-name cleared.

## Product goal

The core interaction is:

**Capture → recognize → click → learn**

The app should help a learner understand Japanese manga without replacing the original manga image with a translated image.

## Supported platforms

Initial targets:

- macOS
- Windows

Do not add Linux/mobile support unless explicitly requested.

## Core product principles

1. Local-first: OCR and dictionary lookup should happen locally.
2. Translation is on-demand, not automatic for every detected text region.
3. Preserve the original manga and render learning information as an overlay/popup.
4. OCR geometry is first-class data. Never reduce OCR output to text-only strings.
5. Vertical Japanese text is a first-class requirement.
6. Account explicitly for physical-pixel vs logical-coordinate scaling (Retina and Windows display scaling).
7. Keep OCR providers replaceable behind an API boundary.
8. Prefer simple implementations over premature abstraction.
9. Implement the smallest slice that proves the current milestone before adding future features.
10. Do not silently guess when OCR confidence is low; expose uncertainty to the UI where appropriate.

## Current architecture

```text
Tauri 2 desktop app
├── React + TypeScript UI
│   ├── Main/settings window
│   ├── Capture selector
│   ├── OCR overlay
│   ├── Word/dictionary popup
│   └── Translation/learning popup
│
└── Rust native layer
    ├── Global shortcut
    ├── Screen capture
    ├── Window/overlay management
    └── OCR process lifecycle

Local OCR service (Python)
├── manga/comic text detection
├── Manga OCR recognition
├── image preprocessing
├── Japanese morphology/tokenization
└── OCR response API

Local data
├── JMdict
├── KANJIDIC2
├── Sudachi dictionary/resources
└── SQLite cache/history

Optional network
└── Translation provider API, only when user requests translation
```

## Planned repository layout

```text
manga-reader/
├── AGENTS.md
├── README.md
├── LICENSE
├── THIRD_PARTY_LICENSES/
├── docs/
│   ├── initial-design.md
│   └── implementation-plan.md
├── apps/
│   └── desktop/
│       ├── src/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── capture/
│       │   │   ├── ocr/
│       │   │   ├── overlay/
│       │   │   ├── dictionary/
│       │   │   └── translation/
│       │   ├── lib/
│       │   └── main.tsx
│       └── src-tauri/
│           └── src/
│               ├── capture/
│               ├── overlay/
│               ├── hotkey/
│               ├── ocr/
│               └── main.rs
├── services/
│   └── ocr/
│       ├── app/
│       │   ├── api/
│       │   ├── detector/
│       │   ├── recognition/
│       │   ├── tokenizer/
│       │   └── pipeline/
│       └── tests/
└── packages/
    └── shared/
        └── src/
```

The structure is a target shape, not a requirement to create every directory immediately. Create files/directories only when the current milestone needs them.

## Technology decisions

### Desktop

- Tauri 2
- React
- TypeScript
- Rust

### Native integration

Use Tauri's global shortcut capability for the capture hotkey.

For cross-platform screen capture, start with a Rust capture abstraction and an xcap implementation. Keep capture code isolated so native macOS ScreenCaptureKit or Windows Graphics Capture can be introduced later if needed.

### OCR

Start with:

1. comic-text-detector for manga/comic text-region detection
2. Manga OCR for Japanese recognition

The detector should produce geometry such as polygons/bounding boxes and text-line information. Manga OCR should be treated as the recognizer, not as the geometry source.

### Japanese analysis

Use Sudachi/Sudachi.rs behind a small application interface. Pin exact versions for reproducibility, especially for dictionary compatibility.

### Dictionary

Use local JMdict data for word lookup and KANJIDIC2 for individual kanji information. Treat dictionary/data licensing separately from software licensing.

### Persistence

Use SQLite for translation cache, OCR/result cache where useful, and user learning history/vocabulary.

### Translation

Define a provider interface. Do not hardcode one vendor into the core domain layer. Initial translation can use one configurable cloud provider; local/offline translation can be added later.

## Shared domain types

The OCR model should preserve geometry and metadata.

```typescript
export interface Point {
  x: number
  y: number
}

export interface TextToken {
  surface: string
  reading: string
  dictionaryForm: string
  start: number
  end: number
  partOfSpeech: string
}

export type TextRegionType =
  | 'dialogue'
  | 'narration'
  | 'soundEffect'
  | 'other'

export interface TextRegion {
  id: string
  text: string
  polygon: Point[]
  orientation: 'horizontal' | 'vertical'
  confidence: number
  type: TextRegionType
  tokens: TextToken[]
}
```

Exact fields may evolve, but geometry must remain part of the public contract.

## OCR API contract

Initial target endpoint:

```http
POST /api/v1/ocr
```

Input:

- screenshot image bytes
- optional OCR options

Output:

- detected/recognized text regions
- polygon/bounding geometry
- orientation
- confidence
- text type when available
- token/reading analysis when the tokenizer stage is enabled

Example conceptual response:

```json
{
  "regions": [
    {
      "id": "region-1",
      "text": "無理のしすぎはダメだよ〜",
      "polygon": [
        {"x": 100, "y": 80},
        {"x": 240, "y": 80},
        {"x": 240, "y": 400},
        {"x": 100, "y": 400}
      ],
      "orientation": "vertical",
      "confidence": 0.98,
      "type": "dialogue",
      "tokens": []
    }
  ]
}
```

Do not make the frontend depend on Python package internals.

## Coordinate rules

Treat these spaces explicitly:

```text
Screen physical pixels
        ↓
Captured image pixels
        ↓
OCR image coordinates
        ↓
Overlay logical coordinates
        ↓
Mouse/event coordinates
```

Never assume these spaces are identical.

On macOS, Retina scaling can create different logical and physical dimensions. On Windows, display scaling such as 125%, 150%, or 200% can do the same.

Maintain a single, tested coordinate-transform path rather than scattered scale calculations.

## Overlay rules

Use a transparent, always-on-top overlay window for OCR interaction.

The overlay should:

- preserve visibility of the manga underneath
- render detected regions and selection/hover states
- receive interaction only where practical
- avoid covering the whole page with opaque UI
- support vertical regions
- anchor popups to the selected region when possible

The overlay should not render or redistribute a translated copy of the manga.

## Capture UX

Initial shortcut concept:

- macOS: Command + Shift + O
- Windows: Control + Shift + O

Use a short capture flow:

```text
hotkey
  ↓
selection overlay
  ↓
user drags region
  ↓
screenshot captured
  ↓
OCR processing
  ↓
interactive overlay
```

Do not add continuous full-screen OCR in the first milestone.

## Learning UX

Word click should provide, where available:

- surface form
- reading
- dictionary form
- meaning
- part of speech

Sentence click should provide:

- original Japanese
- contextual translation
- optional token/grammar explanation

Kanji click should eventually provide:

- character
- on-yomi
- kun-yomi
- meanings
- useful example compounds

Individual character hit-testing can start as an enhancement after region/word click is working.

## Text types

Keep a text type concept because manga contains dialogue, narration, sound effects, and other text. Sound effects should not automatically receive the same learning UI as ordinary dialogue unless the user enables that behavior.

## Translation rules

- Translate only on user request.
- Cache repeated translation requests.
- Keep translation provider code outside OCR/tokenization logic.
- Preserve the original Japanese alongside any translation.
- Send only the minimum necessary context.
- Never upload screenshots automatically just to perform local OCR.

## Licensing and third-party policy

This is an open-source personal project.

Before adding or bundling a dependency, verify the exact version's license and any model/data terms. Maintain `THIRD_PARTY_LICENSES/` and preserve required attribution, notices, and license text.

Current reference projects discussed during design:

- Manga OCR — Apache-2.0 software license in its repository.
- comic-text-detector — GPL-3.0 in its repository.
- Cloe — GPL-3.0 project discussed as a reference application.
- Mokuro — GPL-3.0 project discussed as a reference application.
- Sudachi/sudachi.rs — Apache-2.0 for the relevant software repository; dictionary resources are separate third-party assets.

Do not assume that repository code, model weights, datasets, fonts, or dictionary data all share one license. Verify each bundled asset before release.

Do not copy entire reference applications when only a component is needed. Prefer direct dependencies or clean-room reimplementation of the app-specific layer, while respecting the relevant licenses.

Do not add copyrighted manga screenshots from third-party sites to the public repository. Use user-local fixtures or synthetic/public-domain test assets for automated tests.

## Code quality rules

- Keep TypeScript straightforward and strongly typed.
- Avoid unnecessary generic abstractions.
- Prefer feature-focused modules.
- Use explicit error handling at process/API boundaries.
- Keep OCR, dictionary, and translation concerns separate.
- Add tests around coordinate transforms and OCR response parsing.
- Do not hide platform-specific behavior in magic constants.
- Log useful diagnostics for capture/OCR failures without logging sensitive screenshot contents by default.

## Scope discipline

Do not implement these in the first OCR prototype unless explicitly requested:

- mobile apps
- browser extensions
- continuous background OCR
- automatic full-page reading-order reconstruction
- OCR text replacement/inpainting
- cloud OCR backend
- multi-user accounts
- cloud sync
- advanced Anki integration
- pitch-accent database

## Codex workflow

Before coding:

1. Read this file and the applicable document under `docs/`.
2. Inspect the existing repository rather than assuming it is empty.
3. Confirm the current milestone and implement only that milestone.
4. Identify platform-specific requirements before changing capture/overlay code.
5. Prefer a small vertical slice over creating broad scaffolding.

After coding:

1. Run the relevant tests.
2. Run formatting/linting for changed code.
3. Verify the app still builds for the current target platform where practical.
4. Summarize changed files, tests run, and any platform limitation.
5. Update the implementation-plan status when a milestone is completed.

## Current milestone

The initial implementation target is **Phase 1 + Phase 2** from `docs/implementation-plan.md`:

> Capture a user-selected screen region, run local OCR, return text geometry, and render an interactive transparent overlay aligned with the original screen coordinates.

Do not implement dictionary, translation, or kanji learning UI until the capture → OCR → coordinate → overlay path is working and tested.
