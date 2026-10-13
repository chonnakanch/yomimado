# Code quality review — 2026-10-13

Reviewed frontend service clients and learning-popup state, native capture/window
boundaries, Python API/persistence/dictionary code, and release-tool duplication.
This is a focused source review with local regression checks, not an exhaustive
audit or installed-app acceptance report. The checkout was clean on `develop`
at `fd1f5d3` before the changes.

## Findings fixed

| Priority | Finding and effect                                                                                                                                                          | Change                                                                                                                                                                                                                                        |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P2       | `ocr-client.ts` asserted the JSON response type without checking it. Missing or invalid polygons could reach reading-order and overlay code.                                | Added `ocr-response.ts` to check the envelope, finite polygon coordinates, orientation, confidence, region IDs, review metadata, diagnostics and token offsets before rendering. Unknown confidence (`0`) and vertical geometry remain valid. |
| P2       | Editing the source while a translation was pending cleared the result, but its eventual success/error could repopulate the popup for the previous text.                     | Added a translation request ID guard. Editing invalidates the pending UI update; stale requests cannot change the current result, error or loading state. Regression tests cover stale success and failure while a newer request is pending.  |
| P2       | Translation cache connections used SQLite's transaction context manager, which does not close connections. Database errors also escaped the API as unhandled server errors. | Explicitly close read/write connections on cache hits, misses and exceptions. Return HTTP 503 for SQLite errors, consistent with the vocabulary API.                                                                                          |
| P2       | Saved vocabulary parsing accepted zero and negative IDs even though deletion rejects them.                                                                                  | Require positive safe integer IDs for saved words, matching sentence parsing and deletion.                                                                                                                                                    |
| P3       | Seven frontend clients repeated service URL/HTTP handling; error parsing asserted that FastAPI's `detail` was a string, although validation failures can return an array.   | Centralized transport in `service-client.ts`. Preserve string setup messages and fall back to the endpoint label and HTTP status for malformed/structured details. Endpoint payload validation stays in each client.                          |
| P3       | Editing/reanalyzing popup text repeated the word/kanji/save-state reset sequence.                                                                                           | Extracted `resetWordSelection`, including request invalidation and clearing the kanji loading state.                                                                                                                                          |

The tokenizer's existing Unicode code-point and ordered/non-overlapping token
validation now lives in `token-validation.ts`, shared with OCR response parsing.
No new dependencies, database migrations or visual redesign were introduced.

## Remaining refactor opportunities

These are follow-up maintenance work, not additional confirmed application bugs:

- **Application CI coverage:** `.github/workflows/checks.yml` currently runs three
  release-tool suites. Frontend and OCR service tests ran locally for this change;
  add them to required CI so future application regressions are caught on pushes
  and pull requests. Run Windows-specific Python tests with Python 3.11 or later.
- **Native capture setup:** `get_capture_surface`, `capture_display` and
  `capture_selection` in `apps/desktop/src-tauri/src/lib.rs` repeat selector
  position/size extraction. Display/manual capture also repeat the compositor
  delay and blocking capture dispatch. Extract small helpers in a dedicated
  native refactor, preserving macOS clipping, Windows dispatch and viewport
  differences; verify both platforms before release.
- **Platform smoke requests:** an AST comparison found identical nested `request`
  functions in `scripts/smoke-macos-bundle.py` and
  `scripts/smoke-windows-install.py`. A shared helper could remove this duplication;
  include it in every build/source recipe and preserve platform-specific process
  startup, inference checks and acceptance records.
- **Large orchestration functions:** `TranslationPopup.tsx` still combines
  several learning views and asynchronous workflows. Python
  `recognize_with_models` combines detection, retry/fusion and recognition.
  Extract feature-focused pieces incrementally when changing those features;
  retain geometry and existing synthetic regression fixtures.

## Verification

- Frontend: **99 tests pass**, TypeScript checking and Vite production build pass.
  Prettier checks pass across the desktop project.
- OCR service: **57 tests pass on Python 3.9.6**. The Windows graph checksum test
  initially fails there because `hashlib.file_digest` requires Python 3.11+;
  that test **passes separately on Python 3.13.15**. All 58 tests were exercised
  across the applicable interpreters. No Windows backend compatibility change
  was made. Ruff lint/format checks pass for the changed Python files.
- Native: **36 Rust tests pass** and `cargo build --locked` passes on macOS.
  The build emits an Xcode SDK-discovery/cache warning, with no build errors.
- Existing required release checks: **51 tests pass** across
  `test_desktop_release.py`, `test_macos_ci_release.py` and `test_update_version.py`
  on Python 3.13.15, using local fake APIs.
- `git diff --check` passes. No installer was built or tested on Windows.

## Release implications

The shared Python translation implementation changed. A future macOS release
must prepare and review a new runtime seed containing these changes; the current
frozen seed cannot be silently reused. The existing `verify_reuse` protection
remains in place. Follow `desktop-release.md` for new exact-installer checks and
owner publication approval when a new release is requested.

This review does not bump the version, replace published v0.1.0 assets, change
candidate hashes or extend existing installed-app evidence to new code.
