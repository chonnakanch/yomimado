# Changelog

This log starts with feature work after v0.3.0. Changes under **Unreleased** are
development-source changes and are not included in published installers yet.
Published releases and exact-installer evidence remain in the
[release checklist](docs/desktop-release.md) and
[GitHub releases](https://github.com/chonnakanch/yomimado/releases).

The [feature roadmap](docs/implementation-plan.md#feature-checklist) tracks completed and proposed work.

## Unreleased

### 2026-10-24

#### Fixed

- Wrap bubble translations at whole-word boundaries without automatic hyphens.
  Grow panels in width and height using available capture space before reducing
  the font, while separating neighboring panels and retaining overflow scrolling.
  Correct the Ollama translation prompt so the Japanese question is translated
  instead of answered, stop Hunyuan output at conversation boundaries, and revise
  the cache identity to avoid reusing old conversational answers. The reported
  sentence reproduces the old failure and returns a question through the revised
  local HY-MT2 provider/API, including a fresh result followed by a cache hit.
  All 408 frontend and 272 service tests, formatting/lint, TypeScript/Vite and the
  macOS debug app bundle pass. Browser checks verify whole words, panel growth,
  neighbor separation and scrolling to the final line. Windows interaction and
  exact installers remain unverified. A compatible reviewed macOS runtime seed
  is required before packaging the changed Python service.

- Keep long bubble translations readable instead of replacing the entire sentence
  with an ellipsis. Widen narrow panels within captured space and neighboring-text
  limits, improve English wrapping, and allow overflow to scroll from its first
  line through its last. Preserve popup access and review/selection borders.
  All 407 frontend tests, formatting, TypeScript/Vite, the macOS debug app bundle
  and 216 documentation links pass. Synthetic browser checks verify visible first
  lines and scrolling to the last line; native Windows interaction and exact
  installers remain unverified.

### 2026-10-23

#### Added

- Add an optional **Translate bubbles** toggle to completed OCR overlays. Render
  requested local English translations over detected text bounds, fit legible
  text or show an ellipsis with full-popup access, and reveal Japanese immediately
  when switched off. Keep review outlines, skip known sound effects/demo regions,
  stop queued requests on hide/new scans and expose errors with Retry. Reuse the
  provider-aware service cache and existing coordinate/native input route; do not
  modify manga pixels or save automatically. All 403 frontend and 85 native tests,
  formatting, TypeScript/Vite, Clippy and the macOS debug build pass. Synthetic
  browser checks use mocked translation/native replies; native interaction,
  model inference in this mode, Windows hardware and exact installers remain
  unverified. See [controls](docs/usage.md#translate-in-bubbles) and
  [verification](docs/ui-testing.md#bubble-translation-toggle).

- Add local backup and restore in **Saved → Backup & restore**. Export all saved
  words/sentences, readings, meanings, source text, translations and dates to
  portable JSON with attribution. Preview new/duplicate counts, then atomically
  add missing entries without replacing existing data. Use bounded, native file
  dialogs and complete-file writes; preserve searches and refresh after restore.
  Keep helper text and counts compact, with short Restore/Cancel controls.
  No dependencies or database schema changes. All 392 frontend, 269 service and
  83 native tests, formatting/lint, TypeScript/Vite, Clippy and the macOS debug build
  pass. Native dialogs, Windows and exact installers remain unverified. See
  [controls and limits](docs/usage.md#local-backup-and-restore) and
  [verification](docs/ui-testing.md#local-backup-and-restore). A compatible reviewed
  macOS runtime seed is needed before packaging the changed Python service.

- Extend local conjugation explanations with ている／でいる and casual
  てる／でる, including plain/polite past and negative forms, plus たい desire
  forms with past/negative and polite です variants. Reuse the analyzed verb
  class and exact source spans; show context-dependent meanings explicitly.
  Complete manual selections use the analyzed dictionary form while saving
  preserves the selected Japanese and source sentence. No dependencies, resources
  or service APIs change. All 377 frontend tests, formatting, TypeScript/Vite
  and the macOS debug build pass; see the
  [supported scope](docs/implementation-plan.md#conjugation-behavior-and-supported-forms)
  and [verification limits](docs/ui-testing.md#continuing-actionstate-and-desire-conjugations).

#### Fixed

- Require recognized-row ink coverage before suppressing overlapping OCR fragments.
  Preserve uncovered full/tile/mask text while continuing to skip covered
  duplicates; localized rows no longer trigger the legacy retry overlap filter.
- Preserve non-Japanese warnings through whole-selection and expanded short
  vertical recovery, including expanded-crop diagnostics.
- Keep OCR correction drafts open when Escape belongs to Japanese IME composition,
  including legacy IME key code `229`; ordinary Escape still cancels editing.
  Add 14 model-free service and two popup regressions. All 326 frontend, 239 service
  and 18 OCR/translation contract tests, Ruff, formatting, TypeScript/Vite and the
  macOS debug build pass; 129 local documentation links/fragments were checked.
  Native IME/Windows hardware and new exact installers remain unverified.
  These Python source changes require
  a compatible replacement reviewed macOS runtime seed before packaging; existing
  seed approvals and installer evidence retain their original source identities.

### 2026-10-22

#### Build

- Prepare v0.6.0 from main with the merged OCR geometry, capture/tray and UI
  changes. Update all five app version files and preview PR-only release notes
  from v0.5.0. The changed Python runtime requires a fresh reviewed macOS seed;
  prepare and privately activate the owner-approved replacement while preserving
  the strict compatibility and owner publication gates. See
  [the preparation record](docs/release-preparation-0.6.0.md).

#### Added

- Add **Show OCR results** to the tray/menu bar menu. Restore the retained hidden
  result through the existing display-validated reveal path, without rescanning
  or focusing the toolbar. Disable it during scans, without retained completed
  results and while results are visible; repeated queued Show requests are no-ops.
  Native tests cover the result/scan lifecycle and menu routing. See the
  [verification limits](docs/ui-testing.md#tray-ocr-result-restoration).

#### Changed

- Redesign the reading UI around `#0080FF` blue actions and OCR boxes, copper
  identity marks and charcoal surfaces. Add the copper-frame/blue-bracket app
  icon and matching Windows tray mark; preserve the macOS template. Use 14% blue
  OCR/capture fills, 14 px cards, active Settings fills and Saved tab underlines.
  Refresh the overflow menu and start Settings with its heading.

- Reorganize the learning popup into **Words / Select / Edit**, with grouped
  Copy/Save/Translate actions, temporary Copied feedback, Saved/busy/retry states
  and a collapsible local translation card with separate copying. Add draft-only
  Reset to OCR text and retain explicit apply/cancel, translation and saving.
  Keep the Edit focus ring inside the textarea, shorten Select guidance and
  remove filled hover backgrounds from compound/conjugation disclosures. The
  editor has no character confidence underlines. All 324 frontend tests,
  formatting, TypeScript/Vite and the macOS debug build pass; native WebKit/IME,
  Windows hardware and exact-installer acceptance remain separate. See the
  [design system](docs/design-system.md) and
  [popup verification](docs/ui-testing.md#learning-popup-modes).

- Restore the original `#0866FF` button backgrounds and `#0058E0` hover at the
  owner's request, reverting the muted button palette from `6351025`. Drawing
  outlines and the capture drag box continue to use the same vivid blue.

- Recolor the desktop app icon and Windows tray mark to the charcoal/blue theme.
  Keep the original master as provenance, add a transparent blue master and
  regenerate the desktop PNG, ICO and ICNS exports. Preserve the monochrome
  macOS tray template for system adaptation; record the prompt and regeneration
  recipe in the [design guide](docs/design-system.md#icon-provenance-and-regeneration).

- Give the toolbar book mark a lighter blue than scan actions. Increase keyboard
  focus rings to 3 px, selected Settings category outlines to 3 px and focused
  OCR strokes to 4 px. Remove the slogan and Japanese app-name subtitle from the
  Sources window while preserving its source and licence information.

- Apply charcoal surfaces and `#0866FF` blue actions across the app, with white
  action labels, readable blue links and distinct error feedback. Use blue OCR
  outlines with a thin dark halo and faint hover/selection fill. Match the
  capture drag box to the blue theme and remove the full-screen capture tint,
  preserving a clear view of the manga. Keep the bold X and existing geometry,
  native hit routing and capture lifecycle. See the
  [theme verification](docs/ui-testing.md#charcoal-and-blue-theme).

#### Fixed

- Brighten default OCR outlines to `#0080FF` and hover strokes to `#4D9FFF`.
  Remove the dark halo/black border from OCR polygons while retaining dashed
  review indicators, keyboard focus strokes, original geometry and native hit
  routing. Keep the app buttons and capture drag box styling unchanged.

- Reconcile fragmented horizontal OCR rows when a selection also contains a
  non-Japanese label. Challenge false vertical fragments using complete glyph-row
  evidence, retain separate-column guards and suppress full/tile/mask duplicates
  using recognized-row ink coverage. Keep genuine vertical text and uncovered
  glyphs; warn when the detector classifies a crop as non-Japanese despite
  Japanese-looking recognition. Add 16 regression cases. All 225 service tests,
  seven benchmark-metric tests, 318 frontend tests, Ruff, TypeScript and the
  frontend build pass. Thai OCR remains unsupported; native Windows acceptance is unverified;
  see the [mixed-content record](docs/ocr-mixed-text-results.json).

- Localize loose horizontal OCR title/paragraph detections from visible glyph rows
  on plain light/dark backgrounds. Recover the reproduced title's missing ending,
  avoid pointed stroke-recovery polygons and suppress covered nested fragments.
  Clip polygons to captured image bounds and mark unresolved overlaps for review.
  Preserve original detector diagnostics, source ordering, unknown confidence and
  the existing native coordinate path. Add 15 model-free geometry regressions;
  216 service/benchmark tests and 318 frontend tests, Ruff, frontend formatting,
  TypeScript and the frontend build pass. Native Windows extended-monitor and
  exact-installer acceptance remain unverified; see the
  [measurement record](docs/ocr-geometry-results.json).

### 2026-10-21

#### Removed

- Retire the temporary v0.5.0 publication recovery workflow, helper and tests
  after successful recovery run `39587407949`. Keep Checks and Release, including
  the trusted-main merge trigger. Preserve original artifact/source/installer
  evidence and record the public pre-release outcome. Disable the already
  source-removed historical Actions cleanup workflow in GitHub.

#### Fixed

- Prevent area-selection right-clicks from opening a browser context menu or
  leaving a stale drag. Accept primary-button starts only; secondary-button
  chords, context clicks, cancellation and lost pointer capture clear the drag
  and allow a fresh selection. Disable the browser right-click context menu in all
  app windows. Cover Selected Area, Whole Screen's manual fallback
  and configured reading areas with 12 regression cases. All 315 frontend tests,
  formatting, TypeScript and frontend/current-target native builds pass. Native macOS/Windows
  interaction and exact-installer verification remain unrecorded.

- Open the detector setup's **latest release page** link in the system browser
  through a Settings-only native command, with visible errors and retry if the
  browser cannot open. Follow the upstream `/releases/latest` page instead of a
  fixed release tag. Verify the native macOS launcher and upstream model downloads;
  both the original and current latest downloads match the supported detector's
  SHA-256. See the
  [verification limits](docs/ui-testing.md#detector-release-link-verification).

- Run merged release topics in trusted default-branch context so the main-only
  publication environment accepts them. Retain merged/same-repository/exact-source
  guards and owner review. Add a manual, artifact-pinned recovery for the already
  verified v0.5.0 installers after the original PR deployment was rejected.
  Source/installer hashes and original note content remain unchanged.

#### Build

- Prepare v0.5.0 as a pre-release after PR #26 merged into main. Update all
  five app version files together. Reuse the reviewed OCR runtime seed at
  `46a5649`; source checks, input hashes and preparation limits are recorded in
  [the v0.5.0 preparation record](docs/release-preparation-0.5.0.md). Publication
  and acceptance of the new CI installers remain separate.

#### Added

- Hide completed OCR results with Escape from the reader or a high-contrast X icon
  on the overlay. Keep the result and Rescan state for the toolbar Show toggle.
  Scope Escape to visible completed results, preserving popup/menu/Settings input;
  reject delayed hides during scans or for newer result generations. Reuse native
  hit routing for the measured icon bounds. Native capture smoke was blocked by
  macOS Screen Recording access; [interaction limits](docs/ui-testing.md#completed-overlay-hide-controls)
  remain explicit.

- Custom capture shortcuts in Settings → Scan & OCR. Record Selected Area and
  Whole Screen combinations, apply/save locally on key release and restore both
  defaults. Duplicate, unavailable and unsavable bindings retain the previous
  settings; startup conflicts keep the toolbar usable. Recording an existing
  capture shortcut does not start a scan. Uses the existing native plugin without
  new dependencies or OCR changes. Native macOS editing/duplicate checks pass.
  The owner reported a manual feature pass at `f65576c`.
  All 301 frontend tests and 75 native tests, formatting, Clippy and current-target
  frontend/native builds pass. Windows-specific coverage and exact-installer
  acceptance remain unrecorded.

#### Changed

- Give each requested feature or bug fix a dedicated topic branch and open a PR
  to `main` automatically when the work is complete. Ask the owner to approve
  opening the PR when completion or verification is uncertain; retain separate
  merge and installer-publication authorization.

- Resolve compatible owner-reviewed macOS seeds during Release instead of blocking
  ordinary PR/main Checks on a fixed seed. Bind the selected draft, source, asset
  IDs/hashes/sizes and approval manifest to each run and retain it in source/notices.
  Future owner-activated seeds need no app pin-update PR; the existing reviewed
  seed remains an exact migration fallback. Windows pins and protected installer
  publication are unchanged. Release/source/manifest regression tests and the
  existing seed's real input/archive/mounted-approval verification pass; no new
  installer, source approval or remote seed activation is performed.

- **Documentation maintenance:** remove repeated setup/CI/release descriptions,
  completed UI rollout notes and retired-tool reminders from current guides.
  Correct stale tokenizer/settings descriptions, keep measurement and verification
  evidence in their existing reports, and link each topic to its canonical guide.

- **Installation guide:** add an end-to-end packaged-app walkthrough covering
  platform installers, first launch, macOS capture permission, the exact required
  detector download/import, a first OCR/dictionary/save check and optional local
  translation. Separate contributor setup and correct the implication that
  installed-app users must download dictionaries or start Python manually. Keep
  packaged setup in `docs/installation-guide.md`, reading controls in `usage.md`
  and developer/debug notes in `development.md`; README links to the full setup
  instead of repeating it.

### 2026-10-21

#### Build

- Activate the source-approved macOS OCR runtime seed at `46a5649` for PR #24.
  All four unpublished GitHub inputs match local SHA-256 hashes; revision,
  input hashes and workflow paths change together. Mounted source/signature
  verification, frozen offline learning/persistence smoke and all 29 module
  comparisons pass. Windows inputs and reuse guard rules are unchanged.
  See the [exact source/approval/input record](docs/macos-runtime-review-ocr-20261021.md).
  This adds no new installer acceptance or publication approval.

### 2026-10-20

#### Fixed

- **Small-text and vertical OCR accuracy — initial selection recovery.** Small
  single-region selections can retain a missing edge kana, such as 学校へ
  previously returning 学校. Recovery requires the original recognized substring
  with at least two Japanese script characters and one additional script
  character. Short vertical runs can correct a horizontal detector label when
  both selection and detected bounds support it. Whole-selection results now
  explicitly request review and retain unknown confidence. Uses the existing
  inference calls; local models, dependencies and coordinates are unchanged.
  The original synthetic set improves from 7/10 to 9/10 exact strings and
  7/75 to 5/75 character edits. All 194 service tests, seven benchmark-metric
  tests, 37 frontend response/coordinate tests, Ruff and frontend build pass;
  macOS ONNX CPU source outputs match Torch. Native Windows, private real pages
  and new exact installers remain unverified.
  See [scope and remaining accuracy work](docs/implementation-plan.md#small-text-and-vertical-ocr-accuracy).

#### Added

- **Saved search and dictionary-style library — done in development source,
  UI approved by the owner.** Search words by Japanese surface/base, reading, meaning or source;
  search sentences by Japanese or saved translation. Kana, character width and
  case differences are ignored. Separate queries persist locally. The Saved
  design presents larger headwords and numbered senses with expandable context.
  Existing saved data/order and confirmed removal remain. All 288 frontend tests,
  formatting, TypeScript and frontend build pass. No API/database/dependency
  change; installer publication and acceptance remain separate. See the
  [search behavior and verification](docs/implementation-plan.md#saved-search-limits).

#### Removed

- **Single-bubble OCR retry/redraw**, at the owner's request. Removed its popup
  actions, native commands and capture/session handling, including the multiple
  text-part fix. Check OCR remains a review indicator. Manual OCR text editing
  and ordinary Rescan remain available. The roadmap marks the feature deferred.

Verified with 265 frontend tests, 70 native tests, formatting, TypeScript,
strict Clippy and frontend/macOS native debug builds. Windows native interaction
and exact-installer acceptance were not performed.

#### Changed

- **Documentation consolidation:** combine status/roadmap and short feature notes,
  source/resource architecture, UI specifications and native test checklists.
  Remove 13 superseded/duplicate documents, update README and contributor-agent
  instructions, and index every retained guide. Dedicated release, source/licence,
  build-input and measurement evidence remains unchanged. See the
  [documentation index](docs/README.md).
- **README cleanup:** simplified the feature overview, installation, reading
  flow and documentation links. Removed the obsolete downloads-unavailable
  notice and release history; linked Releases and the detailed checklist instead.
  Development features are distinguished from published installer features.

### 2026-10-19

#### Added

- **Single-bubble OCR retry — subsequently removed on 2026-10-20.** Check OCR opened
  retry and redraw actions for an existing uncertain/approximate region. Only
  that bubble's text and geometry were replaced; unrelated regions and the
  full-page Rescan target were retained. Errors, empty replies, cancellation and
  stale requests preserved the old result. The updated popup reopened and
  retained its review indicator. Used the existing local capture/OCR pipeline.
  See [bubble retry](docs/implementation-plan.md#deferred).
- **Conjugation explanations — done in development source.** Expand Conjugation
  in word details for step-by-step common verb past/negative/polite forms,
  i-adjectives and ちゃう／じゃう contractions. Complete manual expressions can
  reuse their analyzed dictionary base. Unsupported forms stay explicit;
  context-dependent meanings are not inferred. Uses the existing local
  tokenizer with no added dataset, model or dependency. See the
  [supported forms](docs/implementation-plan.md#conjugation-behavior-and-supported-forms).
- **JLPT vocabulary tags — done in development source.** Estimated N5–N1 badges
  in dictionary matches and Saved use a bundled, hash-pinned snapshot of 8,113
  spelling/reading pairs from Jonathan Waller's lists as adapted by Stephen
  Kraus. Matching is reading-sensitive; absent words/readings stay unclassified.
  Reading settings can hide badges across open windows. Full attribution and
  CC BY-SA 4.0 terms are embedded in Sources & licenses. No runtime API, model
  download or Python dependency is added. Original inputs and a reproducible
  offline generator are retained; CI verifies their hashes and generated output.
  See the [data review](THIRD_PARTY_LICENSES/jlpt/README.md).
- **Manual word selection — done in development source.** Select text across or
  within automatic word boundaries, explicitly look up the selection in local
  JMdict, adjust unmatched selections, save the chosen entry with sentence
  context, and explore its kanji. Lookup also works when tokenization fails.
  Unicode offsets and stale-response guards are preserved.
  [Implementation `5b94ee6`](https://github.com/chonnakanch/yomimado/commit/5b94ee6).

#### Fixed

- **Bubble redraw rejecting multiple text regions (removed with the feature on
  2026-10-20):** retry and redraw accepted several detected lines/blocks,
  preserving their individual geometry and tokens. Parts stayed linked so
  another retry replaced the group without duplicates; unrelated bubbles stayed
  intact. Empty/invalid results preserved the previous scan.
- **Toolbar menu clipping and resize cycling:** More actions waits for the
  tray-dependent item list before its first native reveal, then measures the
  full content independently of the constrained scroll viewport. Quit stays
  visible when there is room, or reachable by scrolling on short screens.
  Reserved scrollbar space prevents wrapping from changing as scrolling starts.
- **Saved dictionary identity:** new saves preserve the chosen dictionary
  entry's expression, including alternative matches, so Saved can derive the
  same JLPT label. Existing saved records are not rewritten and need no migration.
- **Visible caret and keyboard selection.** Native arrow keys move the caret;
  Shift + arrow keys extend the selection. Text edits are blocked, including
  typing, deletion, paste, cut and drop, with source restoration for
  non-cancelable input. Caret and selection colors are explicit.
  [Fix `5ddad6c`](https://github.com/chonnakanch/yomimado/commit/5ddad6c).

#### Changed

- **Selection exit label:** renamed **Use word clicks** to **Back to normal**.
  The action leaves selection mode and restores automatic word clicks.
  [Change `e518005`](https://github.com/chonnakanch/yomimado/commit/e518005).
- **Popup layout:** restored the previous layout at the owner's request. The
  compact-controls experiment is reverted and is not a completed feature.
  [Restoration `52fbfba`](https://github.com/chonnakanch/yomimado/commit/52fbfba).

#### Verification and availability

- Historical, before removal: the multiple-part bubble retry fix passed 280
  frontend tests, 78 native tests,
  formatting, TypeScript, strict Clippy and frontend/macOS native debug builds.
  Full native interaction remains unverified under the limitation below.
- Historical, before removal: bubble retry passed 278 frontend tests, 76 native
  tests, formatting, TypeScript,
  strict Clippy and frontend/macOS preview builds. UI layout is checked in the
  browser; the full native retry flow remains unverified after the unsigned
  preview's Screen Recording preflight blocked capture. Windows native checks
  and exact-installer acceptance remain pending.
- Conjugation explanations pass 265 frontend tests, formatting, TypeScript,
  frontend/macOS preview builds and 36 real Lindera/IPADIC examples. Browser
  checks confirm local dictionary lookup and narrow-popup wrapping. Native
  Windows and exact-installer acceptance remain unverified.
- Toolbar sizing passes 209 frontend tests, formatting, TypeScript and the
  frontend/macOS preview builds. Native macOS checks confirm repeated complete
  menu openings and keyboard navigation. Browser checks cover short-screen
  scrolling; Windows native/mixed-DPI interaction remains unverified.
- JLPT tags pass 202 frontend tests and six data/provenance tests, formatting,
  TypeScript, frontend production build and macOS preview build. Browser checks confirm a real
  local dictionary match and immediate cross-window hiding/restoring of tags.
  Windows native interaction and new-installer acceptance are not established.
- The caret fix passed all 197 frontend tests, formatting, TypeScript, frontend
  production build and macOS preview app build. Native macOS checks confirmed
  caret movement, keyboard selection, source protection and local lookup.
- The subsequent label change passed all 26 popup tests, formatting, frontend
  build and macOS preview build.
- Manual selection remains on `develop`; native Windows interaction and
  exact-installer acceptance are unverified. These changes do not approve or
  publish an installer.
