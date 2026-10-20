# Implementation status and feature roadmap

Last reviewed: **2026-10-20**. This is the current plan, not a chronological work
log. [CHANGELOG.md](../CHANGELOG.md) records dated changes; the
[release checklist](desktop-release.md) records publication and exact installers.
Source completion, UI approval and installer acceptance are separate states.
Proposals below do not authorize implementation. Anki export remains excluded
at the owner's request.

## Current status

- The first desktop milestone is complete. Capture, local OCR, scaled overlays,
  dictionary/kanji lookup, explicit translation and local saved collections exist.
- The current source uses Lindera 6.0.0/IPADIC, UniDic-free OCR decoding and
  user-selected local translation through Marian import or Ollama. See
  [architecture and resources](architecture.md) and [model setup](translation-model-selection.md).
- The toolbar, learning popup, Saved, Settings and Sources redesign is implemented;
  the owner approved its phases. Saved search/layout was approved on 2026-10-20.
  [Design specifications](design-system.md) describe the current UI and
  [UI testing](ui-testing.md) retains review evidence and unrecorded native cases.
- The repository's latest recorded public release is **v0.4.0**, source
  `bfdcbf2e313af824155cde6d3b08e27c0d5d2825`, with nine uploaded assets.
  Exact hashes and the retained maintainer acceptance statement are in the
  [release record](desktop-release.md). This status adds no new installer test.
- `main` is the sole integration branch; `develop` is retired. Checks covers
  frontend, service, release tools and both native platforms. A merged
  same-repository `release/*` PR starts Release, which waits for successful
  exact-commit Checks before accessing private inputs. Manual main dispatch is
  available for recovery. Publication requires separate owner approval.
  See [Git conventions](git-conventions.md) and the [release runbook](release-runbook.md).

## Maintenance priorities

- [ ] Triage the Python and Rust findings in the dated
      [security review](security-review-2026-10-13.md). Update exact locks, hashes,
      sources and notices together; do not assume guards patch dependencies.
- [ ] Consider per-launch service authentication. The desktop client header
      guards browser requests; another native process can still supply it.
      Recognition concurrency is already bounded to one worker, including lazy model
      initialization and work continuing after client cancellation.
- [ ] Record future native Windows/mixed-DPI and window lifecycle checks through
      [UI testing](ui-testing.md), without converting browser/CI coverage into a
      physical hardware pass. Actual Ollama inference/download remains unverified in
      the [model-selection evidence](translation-model-selection.md#verification-scope).
- [ ] For the next requested version, follow the release runbook, verify seed
      compatibility and exact private input hashes, then retain source/notices and
      exact-installer evidence. Complete source-only rebuilding remains unverified.
- [ ] Address the [code review's refactor opportunities](code-review-2026-10-13.md#remaining-refactor-opportunities)
      when those areas change; preserve coordinate behavior and platform coverage.

Fresh-Mac testing remains waived in the recorded release disclosure. Windows AMD,
mixed-monitor/left-of-primary and missing-WebView2 hardware cases remain untested.
Preserve historical candidate hashes and waivers. Do not request more v0.1.0
acceptance or publish an installer without a new owner request/authorization.

## Feature checklist

### Implemented in source

- [x] **Manual word selection** — implemented.
- [x] **JLPT vocabulary tags** — implemented.
- [x] **Saved search and dictionary-style library** — implemented; UI approved.
- [x] **Conjugation explanations (initial forms and contractions)** — implemented.

### Planned

- [ ] **Saved tags and organization** — proposed.
- [ ] **Known / learning word states** — proposed.
- [ ] **Personal manga glossary** — proposed.
- [ ] **Local pronunciation playback** — proposed.

Bubble OCR retry/redraw is removed and deferred, not a completed feature.
Anki export remains excluded.

## Completed learning features

The checks below record each feature's implementation-time evidence. Later
publication/acceptance is recorded separately in the [release checklist](desktop-release.md).

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

See the [supported slice and checked examples](implementation-plan.md#conjugation-behavior-and-supported-forms) and
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
[search behavior and verification](implementation-plan.md#saved-search-behavior-and-verification).

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

## Saved search behavior and verification

Status: **approved by the owner and complete in development source — 2026-10-20**.
The owner reviewed and approved the working dictionary-style Saved preview.
Installer publication and exact-installer acceptance remain separate.

### Search

Words match their saved surface, dictionary form, reading, meanings and source
sentence. Sentences match Japanese text and any already-saved translation.
Every whitespace-separated term must occur in at least one of those fields.
Matching ignores letter case, full/half width and hiragana/katakana differences.
There is no romaji conversion or inferred translation.

Search filters the complete existing local collection without changing stored
text, dictionary identities, dates or ordering. It makes no lookup/translation
request and does not create or update saved records. The list API already
returns all records; there is no API or database migration.

Each collection remembers its last query in local storage, up to 200 characters.
Queries remain independent when switching tabs and persist across reopening.
Storage failures leave search usable for the current session. Clear search or
Escape clears a query; Escape does not consume an active IME composition.

Result counts update as the query changes. A no-matches message is distinct from
an empty library and offers Clear search. Refresh keeps the query; a failed
refresh retains the existing rows and error feedback. Remove still requires
confirmation and acts on the selected saved ID, even in a filtered list.

### Approved design

Only Saved changes. It uses the existing dark palette and installed font stacks:
a prominent search field, underlined Words/Sentences tabs, larger Japanese
headwords, readings, JLPT badges and numbered senses. Wider windows place
headwords beside definitions; narrow windows stack them without shrinking text.
Source sentences, saved dates and JMdict attribution remain in an accessible
disclosure. Existing tab navigation, removal focus recovery and errors remain.
No new font, library, model or dataset is added.

The reviewed browser preview uses synthetic sample entries and blocks changes to them.
It does not connect to the real saved database. Its temporary server/harness is
outside the repository. It is a working rendering of the app components rather
than a separate static mockup.

### Verification

All 288 frontend tests, TypeScript, Prettier and the frontend production build
pass. Twenty-three new search cases cover field matching, Unicode normalization,
query persistence, no results, clearing/focus, failed refresh, filtered removal,
storage failures and IME Escape. Existing library lifecycle tests still pass.
Browser checks cover actual search/clear, sentence translation search and source
disclosure, plus a 320 px viewport without horizontal overflow. Native Windows
interaction and exact-installer acceptance remain unverified.

## Conjugation behavior and supported forms

Click a verb or i-adjective stem in the Japanese sentence, then expand
**Conjugation** in its word details. The app includes adjacent analyzed endings
in the explanation while preserving the clicked word and original source text.
For example:

- 食べました → 食べます → 食べる: polite past.
- 食べなかった → 食べない → 食べる: plain negative past.
- 食べちゃった → 食べてしまった → 食べてしまう → 食べる:
  a casual contraction followed by past tense.

The disclosure starts collapsed. Its explanations are possible grammatical
analyses, not sentence translations; context still determines meaning. In
particular, てしまう contractions can convey completion, regret or an unintended
action. The app does not choose one of those meanings from the ending alone.

### Supported slice

| Category                        | Supported forms                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Ichidan and regular godan verbs | Plain past, negative, negative past; polite non-past, past, negative and negative past                                 |
| Irregular verbs                 | する and 来る／くる; IPADIC-marked 行く-type past and 問う-type ウ音便; ある's negative when the analyzed base is ある |
| I-adjectives                    | かった, くない, くなかった; those forms plus です, and dictionary form + です; standalone いい → よい stem             |
| Casual contractions             | ちゃう／ちゃった and じゃう／じゃった, expanded through てしまう／でしまう                                             |

The current implementation relies on the pinned Lindera/IPADIC base form and
verb/adjective class. It generates these small rule families and requires an
exact match to the original expression. It does not infer a class just because
a word ends in る, or infer a dictionary form merely by stripping a suffix.

**Select text → Look up selection** also supports complete, token-aligned
expressions starting with a verb or i-adjective. A recognized expression uses
the analyzed base for the existing local dictionary lookup. Saving retains the
selected surface, chosen dictionary entry and original sentence. Partial-token,
multi-word and unavailable-tokenizer selections do not receive a guessed base.
For 勉強しました, click the verb token し to explain しました; selecting the
whole multi-word predicate is outside this slice.

Unsupported forms show **Conjugation · Not covered** with an explanation.
Passive/potential ambiguity, causatives, progressive forms such as ている／てる,
たい, conditionals, imperatives, copulas/na-adjectives, special honorific classes,
arbitrary compound exceptions and other manga contractions remain future work.
Unsupported manual lookups retain the exact selected expression. Ordinary
dictionary forms and nouns have no extra conjugation disclosure.

Token spans use the existing source code-point offsets. Automatic explanation
does not cross whitespace, punctuation or another independent predicate. Rules
account for the checked IPADIC split 読ん／じゃ／う as well as its ordinary
auxiliary/non-independent verb splits. No tokenizer, OCR geometry, coordinate,
service API, saved database or dependency changes are required.

### Grammar references and verification

The rule code and short explanations are written for YomiMado; no third-party
rule table, grammar dataset, model or source text is bundled. Grammar facts were
checked against the author's published explanations in Tae Kim's guide:

- [Negative verbs](https://guidetojapanese.org/learn/grammar/negativeverbs)
- [Past tense](https://guidetojapanese.org/learn/grammar/past)
- [Adjectives](https://guidetojapanese.org/learn/grammar/adjectives)
- [Polite forms and stems](https://guidetojapanese.org/learn/grammar/polite)
- [てしまう and casual contractions](https://guidetojapanese.org/learn/grammar/unintended)

Unit cases assert literal expansion chains for each supported family, including
godan endings and irregular forms. Other cases cover unsupported/ambiguous
forms, class mismatches, non-contiguous text, Unicode offsets and complete manual
selection. Popup integration checks cover local-only analysis, base-form lookup,
saving, selection changes and unsupported lookups. A local matrix of 36 examples
also passed against the existing pinned Lindera/IPADIC tokenizer.

Browser checks use the real local dictionary/tokenizer service at native popup
width and a narrow 280 px width. Windows native interaction and exact installer
acceptance remain separate checks; this is not an installer release.

## Updating this plan

Update the current status and checklist when scope changes. Put dated development
changes in CHANGELOG; put installer hashes, source approvals, CI release identities
and waivers in the dedicated release records. Reverted experiments must not stay
listed as completed features.

The superseded 1,878-line implementation diary and original design/rollout plans
remain available at [the pre-consolidation source](https://github.com/chonnakanch/yomimado/tree/a5f7ebc/docs).
For example, `rtk git show a5f7ebc:docs/implementation-plan.md` retrieves the full
history, including per-attempt UI evidence and removed bubble-retry work. Active
source, licence, benchmark and exact-installer records remain tracked in docs.
