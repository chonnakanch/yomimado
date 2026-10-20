# YomiMado feature roadmap

Last updated: **2026-10-20**.

This tracks the feature ideas discussed on 2026-10-19. Unchecked features are
proposals for future work, not authorization to implement them. Anki export is
excluded from this roadmap at the owner's request.

**Done** means implemented and verified in development source. It does not mean
published, tested on every supported platform, or accepted for a new installer.
See the [changelog](../CHANGELOG.md) for completed changes and the
[implementation plan](implementation-plan.md) for detailed evidence and release work.

## Feature checklist

### Implemented (unreleased)

- [x] **Manual word selection** — done on `develop`, unreleased.
- [x] **JLPT vocabulary tags** — done on `develop`, unreleased.
- [x] **Saved search and dictionary-style library** — done on `develop`, UI approved, unreleased.
- [x] **Conjugation explanations (initial forms and contractions)** — done on `develop`, unreleased.
- [x] **Small-text and vertical OCR accuracy: initial selection recovery** — implemented
      in source; [scope, evidence and remaining work](implementation-plan.md#small-text-and-vertical-ocr-accuracy).

### Planned

- [ ] **Saved tags and organization** — proposed.
- [ ] **Known / learning word states** — proposed.
- [ ] **Personal manga glossary** — proposed.
- [ ] **Local pronunciation playback** — proposed.
- [ ] **OCR accuracy follow-ups** — page-scale small text, low-contrast dialogue and
      private real-page evaluation; [completion criteria](implementation-plan.md#small-text-and-vertical-ocr-accuracy).

Bubble OCR retry/redraw is removed and deferred, not a completed feature.
Anki export remains excluded.

## Completed

### Manual word selection

Completed on 2026-10-19. Choose **Select text**, select a continuous span across
or within automatic word boundaries, and explicitly choose **Look up selection**.
Unmatched selections remain available to adjust. Dictionary matches can be saved
with their readings, meanings and original sentence; kanji exploration still works.

Mouse dragging and native arrow/Shift + arrow selection are supported. The caret
and selection are visible, source edits are blocked, and **Back to normal** or
Escape leaves selection mode. The previous popup layout is retained.

All 197 frontend tests, formatting, TypeScript, the frontend build and the macOS
preview build pass. Native macOS caret/selection, source protection and local
lookup were checked. Windows interaction and exact installer acceptance remain
unverified. Implementation: [`5b94ee6`](https://github.com/chonnakanch/yomimado/commit/5b94ee6).
See the [dated changelog entries](../CHANGELOG.md#2026-10-19).

### JLPT vocabulary tags

Completed on 2026-10-19. Estimated N5–N1 badges appear beside dictionary matches
and saved words. Reading settings can hide them across open windows. The bundled
Jonathan Waller / Stephen Kraus snapshot contains 8,113 spelling/reading pairs;
unlisted words and missing readings stay unclassified. Full source credits and
CC BY-SA 4.0 terms are available in Sources & licenses. No external API, model
or Python dependency is needed.

New saves retain the selected dictionary expression so the same word/reading
can be labelled in Saved. Existing records and database formats are preserved;
tags are derived from the bundled data rather than persisted in saved records.
The 202 frontend tests and six data/provenance tests pass, including reading
disambiguation, preference synchronization, source hashes and license retention.
Windows interaction and exact-installer acceptance remain unverified. See the
[changelog](../CHANGELOG.md#2026-10-19) and [data review](../THIRD_PARTY_LICENSES/jlpt/README.md).
Kanji/grammar tags and JLPT filtering are separate future scope.
Implementation: [`8ef36bf`](https://github.com/chonnakanch/yomimado/commit/8ef36bf).

### Conjugation explanations

Completed on 2026-10-19. Word details include an expandable **Conjugation**
breakdown for common verb past/negative/polite forms, i-adjectives and
ちゃう／じゃう contractions. Complete manual selections can use the analyzed
base for local lookup and saving. Exact source spans and tokenizer classes are
required; unknown forms stay explicitly unsupported, and contextual nuances
remain uncertain. No external dataset, model, service or dependency is added.

See the [supported slice and checked examples](conjugation-explanations.md) and
[changelog](../CHANGELOG.md#2026-10-19). Broader manga speech, passive/potential,
causatives, progressive forms and other grammar remain future scope.
Implementation: [`53195de`](https://github.com/chonnakanch/yomimado/commit/53195de).

### Saved search and dictionary-style library

Completed and UI-approved on 2026-10-20. Searches saved words by surface, dictionary
form, reading, meaning and source sentence; sentences by Japanese and saved
translation. Matching ignores case, kana script and character width. Separate
queries are remembered locally. The approved dictionary-style Saved layout uses
larger headwords, numbered senses and expandable source details. All 288 frontend
tests, formatting, TypeScript and frontend build pass. Native Windows interaction
and exact-installer acceptance remain unverified. See the
[search behavior and verification](saved-search.md).

Queries remain independent between Words and Sentences, persist across reopening,
and can be cleared with the clear button or Escape. Source sentences, saved dates
and attribution stay accessible. Existing data, newest-first order and confirmed
removal are preserved. No new API, database, model or dependency is required.
Implementation: [`afa6e48`](https://github.com/chonnakanch/yomimado/commit/afa6e48).

## Proposed implementation slices

### Saved tags and organization

Add optional user tags such as manga title and chapter, with filtering in Saved.
JLPT vocabulary badges are already implemented; filtering by their estimated
level remains proposed. User-created tags are separate from those derived levels.

Completion: tags persist locally, existing saved databases remain
readable, and organizing entries never triggers translation or changes their
stored dictionary meanings.

### Known / learning word states

Let users explicitly mark vocabulary as new, learning or known. Show the state
in the popup and Saved, with optional subtle indicators and filters.

Completion: state changes persist locally against a consistent word identity,
can be reversed, and are never inferred merely from scanning or clicking a word.

### Personal manga glossary

Create a local glossary per series for character names, nicknames and special
terms. Let users enter a spelling, reading and note, then show matching glossary
entries alongside dictionary results when that series is selected.

Completion: series can be switched explicitly, glossary entries can be edited
or removed, and personal notes do not overwrite JMdict data or OCR source text.

### Local pronunciation playback

Add explicit play/stop actions for a word or sentence using a local speech
engine. Verify the engine and any voice assets' terms before adding dependencies
or bundling resources. Keep spoken output clearly identified as synthesized.

Completion: playback starts only on request, can be stopped, handles missing
voices visibly, and sends no text to a network speech service.

## Deferred

**Single-bubble OCR retry/redraw** was removed on 2026-10-20 at the owner's
request. It is not an active feature or scheduled implementation. Check OCR
remains a review indicator; manual text correction and ordinary Rescan remain.

## Keeping this roadmap current

When a feature is implemented, check its item and add a dated entry to
[CHANGELOG.md](../CHANGELOG.md) with the implementation commits, verification
and remaining platform limits. Update the detailed implementation plan when a
milestone changes. Keep source completion separate from release publication and
exact-installer acceptance. Reverted experiments must not remain listed as
completed features.
