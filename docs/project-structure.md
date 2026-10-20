# Project structure

YomiMado has three runtime layers: a React interface, a Tauri/Rust desktop host,
and a local Python service. This guide describes the implemented source tree;
the layout in [the initial design](initial-design.md) is a planning reference.
For running the app, start with [development setup](development.md). For reading
manga, use [the reading guide](usage.md).

## Repository map

```text
yomimado/
├── apps/desktop/
│   ├── src/                     React + TypeScript interface
│   │   ├── main.tsx             Selects the view for each native window
│   │   ├── App.tsx              Secondary-window navigation
│   │   ├── features/
│   │   │   ├── toolbar/         Scan controls and More actions menu
│   │   │   ├── capture/         Selection, scan areas, reading order, debug view
│   │   │   ├── overlay/         Interactive OCR region rendering
│   │   │   ├── translation/     Learning popup: words, kanji, selection, translation
│   │   │   ├── library/         Saved words and sentences
│   │   │   └── settings/        OCR setup, translation selection, credits
│   │   ├── lib/                API clients, response validation, coordinates, types
│   │   └── styles/             Shared design tokens and UI primitives
│   ├── src-tauri/
│   │   ├── src/
│   │   │   ├── main.rs         Native executable entry point
│   │   │   ├── lib.rs          Tauri setup, commands, shortcuts, macOS service launch
│   │   │   ├── capture/        xcap capture, page detection, legacy cache cleanup
│   │   │   ├── overlay/        Native overlay/popup placement and input routing
│   │   │   ├── toolbar.rs      Scan sessions, toolbar state, secondary windows
│   │   │   ├── tray.rs         macOS menu bar / Windows notification-area menu
│   │   │   ├── detector_model.rs   Checksum-verified detector import
│   │   │   └── windows_service.rs Windows packaged-service lifecycle
│   │   ├── capabilities/      Tauri command permissions
│   │   ├── tauri.conf.json    Development window/build configuration
│   │   ├── tauri.release.conf.json         macOS packaging overrides
│   │   └── tauri.windows-release.conf.json Windows packaging overrides
│   └── package.json           Frontend commands and dependencies
├── services/ocr/
│   ├── app/
│   │   ├── main.py            FastAPI application and request guards
│   │   ├── models.py          API request/response models
│   │   ├── api/               OCR, learning, translation setup, saved-data routes
│   │   ├── pipeline/          OCR selection, detection/recognition, geometry
│   │   ├── tokenizer/         Lindera/IPADIC adapter and comparison-only Sudachi
│   │   ├── dictionary/        JMdict word index and KANJIDIC2 lookup
│   │   ├── translation.py     Translation provider/cache boundary
│   │   ├── translation_preferences.py  Provider selection and local model imports
│   │   ├── translation_resources.py    Optional model component resources
│   │   ├── ollama_translation.py       Local Ollama integration
│   │   ├── vocabulary.py      SQLite saved words/sentences
│   │   └── security.py        Local request guards and upload limits
│   ├── packaged_main.py       Frozen macOS service entry point
│   ├── windows_packaged_main.py       Windows service launcher/support
│   ├── windows_onnx_packaged_main.py  Windows ONNX entry point
│   ├── windows_onnx_backend.py        Windows inference implementation
│   ├── tests/                 Service, API, geometry and persistence tests
│   └── pyproject.toml         Python dependencies, extras and lint/test settings
├── scripts/                   Resource preparation, inference helpers, release tools
│   └── tests/                 Packaging, release and benchmark contract tests
├── .github/workflows/         Checks and protected desktop release workflow
├── docs/                      Setup, usage, design, investigations, release records
├── THIRD_PARTY_LICENSES/       Software/model/data notices and provenance
├── AGENTS.md                  Contributor-agent instructions and scope
├── CHANGELOG.md               Dated changes and verification limits
└── LICENSE                    YomiMado source licence (GPL-3.0-only)
```

Frontend tests live beside their implementation as `*.test.ts` or `*.test.tsx`.
Rust unit tests live inside the native modules. There is currently no
`packages/shared/` package: the frontend contract is in
[`ocr-types.ts`](../apps/desktop/src/lib/ocr-types.ts), the Python contract is in
[`models.py`](../services/ocr/app/models.py), and
[`ocr-response.ts`](../apps/desktop/src/lib/ocr-response.ts) validates OCR responses
at the frontend boundary.

## How a scan moves through the code

1. The floating toolbar or global shortcut starts a native scan session in
   `toolbar.rs` and `lib.rs`. `main.tsx` selects the capture view for the selector
   window. Selected Area asks for a drag; Whole Screen tries page detection and
   uses a saved/drawn area when necessary.
2. Rust `capture/` captures a PNG in memory and supplies the display/crop metadata.
   `CaptureSelector.tsx` coordinates the capture and calls `lib/ocr-client.ts`,
   which uploads the image to the local service.
3. Python `api/ocr.py` validates the request and runs `pipeline/`. The detector
   supplies regions and orientation; Manga OCR supplies text. An unconfigured
   development service returns a labeled demo boundary instead of OCR text.
4. The frontend validates the response, uses `lib/coordinates.ts` to map image
   polygons into overlay logical coordinates, and asks the Rust overlay module
   to show the result. `OcrOverlay.tsx` renders the interactive regions.
5. Clicking a region opens `TranslationPopup.tsx`. Its API clients request word
   analysis, dictionary entries and kanji details from the Python service.
   Translation and saving run only after explicit user actions.

Preserve polygons, orientation and review metadata across these boundaries.
Capture pixels, OCR image coordinates and overlay logical coordinates differ on
Retina/scaled displays. Token offsets use Unicode code points, not JavaScript
UTF-16 indices. Recognition confidence `0` means unknown, and approximate regions
carry review metadata. See [resources and data flow](app-resources.md) for the
model, dictionary and storage details.

## Local service usage

Development runs the service separately at `http://127.0.0.1:8765`; `tauri dev`
does not start it. Packaged apps start their bundled service on port `8766`.
Frontend requests go through `src/lib/service-client.ts`; release builds configure
the packaged URL. `VITE_OCR_URL` overrides the frontend URL at Vite startup/build
time. Keep the service bound to loopback.

| Route                                           | Purpose                                                                  |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| `GET /health`                                   | Service availability and selected OCR engine; does not prove models load |
| `POST /api/v1/ocr`                              | Multipart PNG field `image`; optional form field `debug`                 |
| `POST /api/v1/tokenize`                         | Japanese text to word tokens with source offsets                         |
| `POST /api/v1/word`                             | Local JMdict lookup for a surface/base form/reading                      |
| `POST /api/v1/kanji`                            | Local KANJIDIC2 meanings and readings                                    |
| `POST /api/v1/kanji/examples`                   | Local JMdict example compounds                                           |
| `POST /api/v1/translate`                        | Explicit text translation using the selected local provider/cache        |
| `GET/POST /api/v1/translation-settings`         | Inspect or select the translation provider                               |
| `POST /api/v1/translation-settings/import`      | Import a compatible local Marian model folder                            |
| `GET /api/v1/translation-settings/ollama`       | Inspect local Ollama availability/models                                 |
| `POST /api/v1/translation-settings/ollama/pull` | Explicitly request an Ollama model download                              |
| `GET/POST /api/v1/vocabulary`                   | List or save words                                                       |
| `DELETE /api/v1/vocabulary/{word_id}`           | Remove a saved word                                                      |
| `GET/POST /api/v1/sentences`                    | List or save sentences                                                   |
| `DELETE /api/v1/sentences/{sentence_id}`        | Remove a saved sentence                                                  |

All `/api/` calls require `X-YomiMado-Client: desktop`. For example, after starting
the development service, run these from a terminal; replace the PNG path with
your own local or synthetic fixture:

```sh
curl --fail-with-body http://127.0.0.1:8765/health
curl --fail-with-body http://127.0.0.1:8765/api/v1/ocr -H 'X-YomiMado-Client: desktop' -F 'image=@/absolute/path/capture.png;type=image/png'
```

On Windows PowerShell, use `curl.exe` for these examples. For full JSON schemas,
open `http://127.0.0.1:8765/docs` while the service is running. Use a client such as
curl to supply the required header for API calls. API routes and Pydantic models
are the source of truth for request fields. The header is a browser request
guard, not a secret.

## Where to make changes

| Task                                     | Start here                                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| Change toolbar controls or scan feedback | `src/features/toolbar/`, native `toolbar.rs`                                  |
| Change capture or page cropping          | Native `capture/`, `src/features/capture/`                                    |
| Fix alignment or hit testing             | `src/lib/coordinates.ts`, native `overlay/`, `src/features/overlay/`          |
| Change OCR detection or recognition      | `services/ocr/app/pipeline/`; Windows backend for packaged Windows            |
| Change token boundaries or readings      | `services/ocr/app/tokenizer/`                                                 |
| Change dictionary lookup                 | `services/ocr/app/dictionary/` and `app/api/word.py` / `kanji.py`             |
| Change the learning popup                | `src/features/translation/`                                                   |
| Change saved collections                 | `src/features/library/`, service `vocabulary.py` and `api/vocabulary.py`      |
| Change translation setup/provider        | `src/features/settings/`, service `translation*.py` / `ollama_translation.py` |
| Change installer/source delivery         | `scripts/`, `.github/workflows/release.yml`, platform release configs         |

Here `src/` and native paths refer to `apps/desktop/src/` and
`apps/desktop/src-tauri/src/`, respectively. Use
[development checks](development.md#local-checks) for the affected layer.
Packaging and source-delivery scripts have their own
[script guide](../scripts/README.md) and [release checklist](desktop-release.md).

## Generated and user-local files

`node_modules/`, `dist/`, Rust `target/`, Python `.venv/`, `*.egg-info/` and
generated Tauri schemas are build/development outputs. The git-ignored
`services/ocr/local-models/`, `local-dictionaries/`, `local-fixtures/`,
`services/ocr/build/` and `apps/desktop/src-tauri/resources/ocr/` hold local assets
and staging data. Do not commit manga screenshots, model downloads or local
databases. In contrast, tracked manifests, locks and licence records under
`docs/` and `THIRD_PARTY_LICENSES/` are required source/build inputs.

Saved learning data and translation caches are outside the source tree by
default; standalone development and packaged apps use different storage paths.
See [development setup](development.md) for paths and environment overrides,
[dictionary updates](dictionary-updates.md) for resource maintenance, and
[implementation status](implementation-plan.md) for source-versus-installer
verification. New installer publication still requires owner authorization.
