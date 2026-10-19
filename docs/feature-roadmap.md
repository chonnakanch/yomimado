# YomiMado feature roadmap

This tracks the feature ideas discussed on 2026-10-19. Unchecked features are
proposals for future work, not authorization to implement them. Anki export is
excluded from this roadmap at the owner's request.

**Done** means implemented and verified in development source. It does not mean
published, tested on every supported platform, or accepted for a new installer.
See the [changelog](../CHANGELOG.md) for completed changes and the
[implementation plan](implementation-plan.md) for detailed evidence and release work.

## Feature checklist

- [x] **Manual word selection** — done on `develop`, unreleased.
- [x] **JLPT vocabulary tags** — done on `develop`, unreleased.
- [ ] **Saved search and organization** — proposed.
- [x] **Conjugation explanations (initial forms and contractions)** — done on `develop`, unreleased.
- [x] **Retry OCR for one speech bubble (existing regions)** — done on `develop`, unreleased.
- [ ] **Known / learning word states** — proposed.
- [ ] **Personal manga glossary** — proposed.
- [ ] **Local pronunciation playback** — proposed.

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
unverified. See the [dated changelog entries](../CHANGELOG.md#2026-10-19).

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

### Retry OCR for one speech bubble

Completed on 2026-10-19 for existing regions. The popup's **Check OCR** indicator
opens **Retry bubble OCR** and **Redraw bubble bounds**. A successful local retry
replaces only that region and reopens its popup; other regions, stable IDs and the
original full-area Rescan target are preserved. Failures/cancellation retain the
old result, and retries remain marked for review rather than claiming certainty.

See the [retry workflow and limits](bubble-ocr-retry.md). Adding an entirely
missed bubble without an existing region is future scope. Windows native and
exact-installer verification remain separate from development completion.

## Proposed implementation slices

### Saved search and organization

Search saved words by Japanese surface, reading or stored meaning. Add optional
user tags such as manga title and chapter, with filtering in Saved. JLPT filters
can follow once vocabulary tags are available.

Completion: searches and tags persist locally, existing saved databases remain
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

## Keeping this roadmap current

When a feature is implemented, check its item and add a dated entry to
[CHANGELOG.md](../CHANGELOG.md) with the implementation commits, verification
and remaining platform limits. Update the detailed implementation plan when a
milestone changes. Keep source completion separate from release publication and
exact-installer acceptance. Reverted experiments must not remain listed as
completed features.
