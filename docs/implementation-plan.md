# Implementation status and feature roadmap

Last reviewed: **2026-10-23**. This is the current plan, not a chronological work
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
- Toolbar, learning popup, Saved, Settings and Sources UI are implemented. Current
  contracts are in [design specifications](design-system.md); native checks and
  dated review evidence are in [UI testing](ui-testing.md).
- Horizontal OCR geometry recovery localizes loose titles and plain light/dark
  paragraphs into bounded text rows, retaining review metadata. Mixed-content
  recovery reconciles fragmented rows and suppresses false vertical runs using
  combined ink coverage. Box overlap alone cannot suppress uncovered full/tile/mask
  text; non-Japanese warnings survive selection and expanded-crop recovery.
  Source checks and
  [synthetic measurements](ocr-geometry-results.json) pass; native Windows
  extended-monitor acceptance remains unrecorded.
- Detector setup's release link opens the latest upstream page in the system
  browser, with launch errors shown in Settings. The native macOS link and exact
  download hash are [verified in development](ui-testing.md#detector-release-link-verification).
- Area selection accepts primary-button drags and resets interrupted/context-click
  drags. All app windows suppress the browser right-click context menu. Drag
  regression coverage passes; native macOS/Windows interaction checks remain unrecorded in
  [UI testing](ui-testing.md#check-the-native-interaction).
- OCR correction preserves the draft when Escape belongs to Japanese IME
  composition; ordinary Escape still cancels editing. Regression coverage is
  recorded with [popup verification](ui-testing.md#learning-popup-modes).
- The latest public release is **v0.5.0**, source
  `8ff3be2621096a9804cc23ba33902f5aab34da55`, with nine uploaded assets.
  It includes custom capture shortcuts and initial OCR recovery using reviewed
  seed `46a5649`. [Publication recovery](release-recovery-0.5.0.md) succeeded;
  its temporary workflow is retired. Exact hashes and verification limits remain
  in the [release checklist](desktop-release.md). This records hosted publication,
  not a new local installer or hardware test.
- Integration and release procedures are maintained in
  [Git conventions](git-conventions.md) and the [release runbook](release-runbook.md).
  Release dynamically selects an owner-reviewed compatible macOS seed; ordinary
  PR Checks do not block on seed availability.
- **v0.6.0 is prepared on `release/0.6.0`**, including the merged OCR geometry,
  capture/tray and UI changes. Local application/release checks and the initial
  six hosted Checks pass. The fresh macOS runtime seed is owner-approved and
  privately activated; it covers the changed Python service. Main integration
  and publication remain
  separate. See the [preparation record](release-preparation-0.6.0.md).

The current private macOS runtime seed binds reviewed source `194dd57`, including
horizontal/mixed-content geometry recovery. Actual source approval, four uploaded
input hashes and the owner-uploaded activation manifest are retained in the
[seed record](macos-runtime-seed.md#v060-replacement-seed--2026-10-22).
Mounted source/signature and frozen offline smoke checks pass; this does not
change published installers or establish new exact-installer acceptance.
Later Python service fixes require a compatible replacement reviewed runtime seed
before packaging; the recorded approval applies only to its bound source.

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
      [translation verification record](ui-testing.md#translation-model-verification--2026-10-18).

Exact-installer acceptance, source-only rebuild limits and hardware waivers are
recorded in the [release checklist](desktop-release.md).

## Feature checklist

### Implemented in source

- [x] **Show OCR results from the tray** — restore the latest hidden completed
      outlines without rescanning or focusing the toolbar; scan/no-result/visible
      guards remain active. [Controls](usage.md#tray--menu-bar) and
      [verification limits](ui-testing.md#tray-ocr-result-restoration).

- [x] **Charcoal and blue theme** — shared `#0866FF` actions, brighter blue OCR outlines
      without black borders, a blue capture drag box on a transparent selector,
      and matching desktop/Windows tray icons;
      [design contract](design-system.md#2-semantic-color-tokens) and
      [verification limits](ui-testing.md#charcoal-and-blue-theme).

- [x] **Hide completed OCR results with Escape or an overlay icon** — implemented;
      results can be restored through the toolbar. [Controls](usage.md#scanning)
      and [verification limits](ui-testing.md#completed-overlay-hide-controls).

- [x] **Custom capture shortcuts** — Selected Area and Whole Screen can be recorded
      in Settings, saved locally and applied immediately, with conflict handling
      and Restore defaults; [controls](usage.md#customize-capture-shortcuts).

- [x] **Manual word selection** — implemented.
- [x] **Popup reading modes and action states** — Words, Select and Edit share
      explicit copy/save/translation controls; correction reset, transient copy
      feedback, saved/busy/retry states and a collapsible local translation card.
      [Controls](usage.md#learning-popup) and
      [verification limits](ui-testing.md#learning-popup-modes).
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

Current reading behavior is documented in [usage](usage.md); dated implementation
commits and checks are in [CHANGELOG.md](../CHANGELOG.md).

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

### Horizontal geometry recovery

The horizontal title/paragraph geometry follow-up is implemented in source.
It recovers the reproduced large title's missing ending and separates plain
light/dark paragraph rows while retaining review metadata. Mixed-content selection
recovery also reconciles competing fragments before column guards and removes
covered full/tile/mask duplicates only after row recognition. Non-Japanese detector
classifications remain separate and explicitly uncertain. Thai recognition and
reliable script identification are not implemented; low-contrast and recognition
errors remain. [Runtime behavior](architecture.md#resources-and-data-flow),
[measurements](ocr-geometry-results.json) and
[mixed-content checks](ocr-mixed-text-results.json), plus
[native acceptance cases](ui-testing.md#horizontal-ocr-geometry-recovery) describe
the supported scope; native Windows extended-monitor verification is still pending.

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

## Saved search limits

User controls and matching behavior are in [Saved words and sentences](usage.md#saved-words-and-sentences).
The implementation keeps independent local queries for Words and Sentences,
limited to 200 characters each. Storage failure must leave search usable for the
current session. IME composition must not be interrupted by Escape. Filtering
must preserve stored text, record IDs, newest-first ordering and confirmation of
removal; failed refresh keeps the existing rows and query.

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
auxiliary/non-independent verb splits.

### Grammar references

The rule code and short explanations are written for YomiMado; no third-party
rule table, grammar dataset, model or source text is bundled. Grammar facts were
checked against the author's published explanations in Tae Kim's guide:

- [Negative verbs](https://guidetojapanese.org/learn/grammar/negativeverbs)
- [Past tense](https://guidetojapanese.org/learn/grammar/past)
- [Adjectives](https://guidetojapanese.org/learn/grammar/adjectives)
- [Polite forms and stems](https://guidetojapanese.org/learn/grammar/polite)
- [てしまう and casual contractions](https://guidetojapanese.org/learn/grammar/unintended)

Earlier implementation diaries and rollout attempts remain in
[Git history](https://github.com/chonnakanch/yomimado/tree/a5f7ebc/docs).
Follow [documentation maintenance](../AGENTS.md#documentation-maintenance) when
updating this plan.
