# Changelog

This log starts with feature work after v0.3.0. Changes under **Unreleased** are
development-source changes and are not included in published installers yet.
Published releases and exact-installer evidence remain in the
[release checklist](docs/desktop-release.md) and
[GitHub releases](https://github.com/chonnakanch/yomimado/releases).

The [feature roadmap](docs/feature-roadmap.md) tracks completed and proposed work.

## Unreleased

### 2026-10-19

#### Added

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
