# Implementation status and feature roadmap

Last reviewed: **2026-10-21**. This is the current plan, not a chronological work
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

Release notes use GitHub PR titles/numbers and source/hash-bound previews. The
optional git-cliff commit-audit tool was retired on 2026-10-20; the
[release runbook](release-runbook.md#generate-and-review-release-notes) describes
the current procedure. Its historical removal evidence remains at source
`dcb3d7d`.

The private macOS runtime seed now binds reviewed source `46a5649`, including
initial small-selection OCR recovery. Source approval and all four uploaded hashes
are recorded in the [OCR seed review](macos-runtime-review-ocr-20261021.md).
Mounted source/signature and frozen offline smoke checks pass; this does not
change the published v0.4.0 installer or establish new exact-installer acceptance.

## Maintenance priorities

- [ ] **Revalidate dependency/security findings.** Compare the dated
      [security review](security-review-2026-10-13.md) with current Python/Rust
      inventories and upstream advisories, then record which findings still apply.
      Any dependency update must retain matching locks, hashes, sources and notices.
- [ ] **Decide on per-launch service authentication.** The desktop client header
      guards browser requests; another native process can still supply it. Record
      the decision and scope before implementing authentication. Existing one-worker
      recognition admission remains in place.
- [ ] **Complete unrecorded native UI checks.** Use the Windows/mixed-DPI and
      window lifecycle cases in [UI testing](ui-testing.md), recording source,
      hardware and results. Browser/CI coverage does not establish a hardware pass.
- [ ] **Verify real Ollama inference and downloads.** Exercise model download,
      explicit selection, translation and failure recovery against a running local
      Ollama instance. Retain results with the
      [model-selection evidence](translation-model-selection.md#verification-scope).

Fresh-Mac testing remains waived in the recorded release disclosure. Windows AMD,
mixed-monitor/left-of-primary and missing-WebView2 hardware cases remain untested.
Complete source-only rebuilding remains unverified in the
[release record](desktop-release.md).
Preserve historical candidate hashes and waivers. Do not request more v0.1.0
acceptance or publish an installer without a new owner request/authorization.

## Feature checklist

### Implemented in source

- [x] **Manual word selection** — implemented.
- [x] **JLPT vocabulary tags** — implemented.
- [x] **Saved search and dictionary-style library** — implemented; UI approved.
- [x] **Conjugation explanations (initial forms and contractions)** — implemented.
- [x] **Small-text and vertical OCR accuracy: initial selection recovery** — implemented;
      [scope and evidence](#small-text-and-vertical-ocr-accuracy).

### Planned

- [ ] **Saved tags and organization** — proposed.
- [ ] **Known / learning word states** — proposed.
- [ ] **Personal manga glossary** — proposed.
- [ ] **Local pronunciation playback** — proposed.
- [ ] **OCR accuracy follow-ups** — page-scale small text, low-contrast dialogue and
      private real-page evaluation; [completion criteria](#small-text-and-vertical-ocr-accuracy).

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

## Small-text and vertical OCR accuracy

The initial selection-recovery slice is implemented in development source.
Ordinary scans of selections up to 320 × 320 captured image pixels can recover
one omitted Japanese character, such as 学校へ previously returning 学校. The
whole-selection result must retain the complete recognized substring, containing
at least two Japanese script characters, and add exactly one Japanese script
character. A punctuation-only addition, changed reading or one-character seed
does not qualify for this new rule. The existing longer-text fallback remains.

When that fallback recovers a short run, a horizontal detector label can become
vertical only when both the selection and detected bounds are at least 1.5 times
taller than wide, and the original text contains one to three Japanese script
characters. Capture shape alone cannot change a detected horizontal line.
Recovered text keeps the whole selection's image-space polygon, explicit review
metadata and unknown confidence (`0`). The original detector result remains in
debug output. Recognition uses the existing full-selection call: there are no
additional inference passes, models, dependencies or coordinate transformations.

- [x] Recover a single missing edge character in small, single-region selections.
- [x] Correct supported short vertical selection orientation and expose uncertainty.
- [ ] Improve page-scale small-text detection/cropping while keeping adjacent
      dialogue and furigana separate.
- [ ] Recover low-contrast dialogue without joining separate text regions.
- [ ] Evaluate private real-page fixtures across both supported native platforms.

Follow-up changes must improve measured character errors or missed text without
regressing blank/artwork negatives, neighboring regions or image-space geometry;
record inference counts and scan-time cost alongside accuracy. This milestone
does not restore the removed single-bubble retry/redraw UI.

Verification and synthetic accuracy measurements are recorded with the
[OCR accuracy results](small-text-accuracy-results.json). These do not establish a
general manga accuracy rate or acceptance of a new installer.

The retained comparison uses `04c9617` as baseline, unchanged local models,
two alternating repetitions and 13 synthetic images (52 scans). On the original
nine images, exact reference strings improve from 7/10 to 9/10 and character
edits from 7/75 to 5/75 (9.3% → 6.7% CER). With the sparse-page fixtures, exact
strings improve from 10/13 to 12/13 and edits from 7/84 to 5/84. Only the small
horizontal/vertical selection responses change; low-contrast dialogue remains
incorrect. The larger selection polygons represent approximate recovery areas,
not improved detector localization; strict box-IoU scores are retained in the
results. Detector and recognition call counts are unchanged. Pooled scan medians
are 1,072 → 1,100 ms; the small uncontrolled sample establishes no speedup.

All 194 service tests (including 25 new recovery cases), seven benchmark-metric
tests, 37 frontend response/coordinate tests, Ruff and the frontend production
build pass. A separate ONNX CPU source run on macOS matches all nine Torch
candidate responses with Torch/Manga OCR/UniDic/Fugashi imports blocked. Native
Windows, private real manga and new exact installers remain unverified.

Reproduce the retained source comparison with existing local resources:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/benchmark_detector_retries.py \
  --baseline-ref 04c9617 --repeats 2 --skip-no-tiles \
  --output services/ocr/build/small-text-accuracy-20261020/sequential
```

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
