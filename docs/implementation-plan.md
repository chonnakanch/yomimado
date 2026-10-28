# Implementation status and feature roadmap

Last reviewed: **2026-10-28**. This is the current plan, not a chronological work
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
- The latest public release is **v0.6.0**, source
  `e1d75bd4e8aab9d659bf22f089070dd2a1328f3e`, published on 2026-10-22 with nine
  uploaded assets. It includes the OCR geometry, capture/tray and UI changes using
  reviewed seed `194dd57`. Exact hashes and verification limits remain in the
  [release checklist](desktop-release.md). This records hosted publication,
  without new local installer or hardware acceptance.
- Integration and release procedures are maintained in
  [Git conventions](git-conventions.md) and the [release runbook](release-runbook.md).
  Release dynamically selects an owner-reviewed compatible macOS seed; ordinary
  PR Checks do not block on seed availability.
- **v0.7.0 is prepared on `release/0.7.0`**, including merged PRs #39–#45.
  Local application/release checks pass. The changed Python service requires a
  replacement runtime seed; its private candidate and unsigned source delivery
  are prepared for owner review. Source approval, private activation, main
  integration and exact-installer publication remain separate. See the
  [preparation record](release-preparation-0.7.0.md).

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
      Ollama instance. HY-MT2 inference and a 27-region native macOS overlay were
      checked on 2026-10-24; download/selection/failure-recovery acceptance remains
      open. Retain results with the
      [translation verification record](ui-testing.md#translation-model-verification--2026-10-18).

Exact-installer acceptance, source-only rebuild limits and hardware waivers are
recorded in the [release checklist](desktop-release.md).

## Feature checklist

### Implemented in source

- [x] **Auto detect page changes** — explicit, default-off scan-and-repeat icon watches
      the last successful manga area and uses settled image changes to start local
      Rescan. Popup/secondary-window pauses, self-overlay masks, single-scan
      admission, Stop/late-result guards, blank-page continuation and display/error
      shutdown are implemented. No automatic capture at launch or cloud OCR.
      [Controls and limits](usage.md#auto-detect-page-changes) and
      [verification](ui-testing.md#auto-detect-page-changes).

- [x] **Automatic translated text over bubbles** — a persisted opt-in setting in
      Settings → Reading starts local translations after each completed scan;
      disabling it immediately reveals Japanese. Sequential requests,
      error/retry, word wrapping without added hyphens, panels that grow in width and
      height, saved font-size choices (Automatic or fixed 12–32 px), and scrollable
      long text with full-popup access. Defaults off; enabling persists across scans/restoration/restarts.
      No image modification or bubble segmentation.
      [Controls](usage.md#translate-in-bubbles) and
      [verification limits](ui-testing.md#bubble-translation-toggle).

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
- [x] **Saved vocabulary highlights** — Words mode marks saved dictionary
      spellings directly in the Japanese sentence, including analyzed inflections
      and exact complete-token expressions. Reuses Saved without status controls;
      updates after saving, removing and restoring words. [Behavior and limits](usage.md#learning-popup)
      and [verification](ui-testing.md#saved-vocabulary-highlights).
- [x] **Popup reading modes and action states** — Words, Select and Edit share
      explicit copy/save/translation controls; correction reset, transient copy
      feedback, saved/busy/retry states and a collapsible local translation card.
      [Controls](usage.md#learning-popup) and
      [verification limits](ui-testing.md#learning-popup-modes).
- [x] **JLPT vocabulary tags** — implemented.
- [x] **Saved search and dictionary-style library** — implemented; UI approved.
- [x] **Local backup and restore** — export all saved words/sentences to portable
      JSON, preview new/duplicate counts and restore missing entries atomically;
      [controls and limits](usage.md#local-backup-and-restore) and
      [verification](ui-testing.md#local-backup-and-restore).
- [x] **Conjugation explanations** — initial forms, ちゃう／じゃう contractions,
      continuing-action/state ている／てる, desire たい, ambiguous
      potential/passive/honorific forms, causatives, ば／たら conditionals and
      analyzed commands are implemented;
      [supported forms](#conjugation-behavior-and-supported-forms).
- [x] **Small-text and vertical OCR accuracy: initial selection recovery** — implemented;
      [scope and evidence](#small-text-and-vertical-ocr-accuracy).

### Planned

- [ ] **Saved tags and organization** — proposed.
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
- 読んでた → 読んでいた → 読んでいる → 読む:
  a casual continuing-action/state contraction followed by past tense.
- 食べたくなかった → 食べたくない → 食べたい → 食べる:
  negative past of the desire form.
- 食べられた → 食べられる → 食べる: past of a shared
  potential/passive/honorific form; the app does not choose a meaning.
- 読ませました → 読ませます → 読ませる → 読む: polite past causative.
- 行けば → 行く; 読んだら → 読んだ → 読む: conditional forms.
- 待て → 待つ: a command confirmed by the analyzed imperative feature.

The disclosure starts collapsed. Its explanations are possible grammatical
analyses, not sentence translations; context still determines meaning. In
particular, てしまう contractions can convey completion, regret or an unintended
action. Likewise, ている can describe an ongoing action, repeated activity or
resulting state. The app does not choose a context-specific meaning or infer who
wants an action from たい alone.
Likewise, causatives can mean making or letting someone act. The shared
られる form can express ability, passive voice or respectful speech; godan
れる forms can express passive voice or respectful speech. These interpretations
stay explicit rather than being resolved from the suffix alone. Conditional
たら／だら uses a past-form construction but does not by itself place the
condition in the past.

### Supported slice

| Category                        | Supported forms                                                                                                                                                                                |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ichidan and regular godan verbs | Plain past, negative, negative past; polite non-past, past, negative and negative past                                                                                                         |
| Irregular verbs                 | する and 来る／くる; IPADIC-marked 行く-type past and 問う-type ウ音便; ある's negative when the analyzed base is ある                                                                         |
| I-adjectives                    | かった, くない, くなかった; those forms plus です, and dictionary form + です; standalone いい → よい stem                                                                                     |
| Casual contractions             | ちゃう／ちゃった and じゃう／じゃった, expanded through てしまう／でしまう                                                                                                                     |
| Continuing action/state         | ている／でいる and casual てる／でる; plain non-past, past, negative and negative past; polite ます, ました, ません and ませんでした, including forms with い omitted                          |
| Desire                          | たい, たかった, たくない and たくなかった; each also with polite です                                                                                                                          |
| Potential/passive/honorific     | Ichidan and analyzed カ変 られる forms retain all three interpretations; godan and する passive/honorific forms retain both. Plain non-past, past, negative, negative past and polite variants |
| Causative                       | せる／させる families for the supported analyzed classes, with plain non-past, past, negative, negative past and polite variants; make/let remains contextual                                  |
| Conditionals                    | Positive and negative ば and たら／だら for verbs and i-adjectives; the same adjective rules also cover たい conditionals                                                                      |
| Commands                        | Godan e-row, ichidan ろ／よ, する → しろ／せよ and 来る／くる → 来い／こい when IPADIC supplies an imperative feature; くれる's exception is not treated as regular ろ／よ                     |

The current implementation relies on the pinned Lindera/IPADIC base form and
verb/adjective class. It generates these small rule families and requires an
exact match to the original expression. It does not infer a class just because
a word ends in る, or infer a dictionary form merely by stripping a suffix.
For example, real IPADIC output gives 読める its own ichidan dictionary form,
so the app does not reconstruct 読む or する from 読める or できる. A bare
書け can likewise be analyzed as a stem of 書ける, without an imperative
feature, and remains **Not covered**. The supplied lexical analysis is retained;
the frontend does not silently substitute a more convenient root or class.

**Select text → Look up selection** also supports complete, token-aligned
expressions starting with a verb or i-adjective. A recognized expression uses
the analyzed base for the existing local dictionary lookup. Saving retains the
selected surface, chosen dictionary entry and original sentence. Partial-token,
multi-word and unavailable-tokenizer selections do not receive a guessed base.
For 勉強しました, click the verb token し to explain しました; selecting the
whole multi-word predicate is outside this slice.

Unsupported forms show **Conjugation · Not covered** with an explanation.
Copulas/na-adjectives, special honorific classes, arbitrary compound exceptions
and other manga contractions remain future work. Auxiliary chains such as
causative-passive させられる, passive + ている, ていたい and てしまっている,
connecting ていて／たくて and alternative polite negative たくありません are
outside this slice. Passive/causative conditional combinations, shortened causatives,
ら-dropped potential forms, と／なら conditions and negative commands are also
outside this slice; ordinary dictionary forms followed by an unsupported particle
can have no conjugation disclosure.
Unsupported manual lookups retain the exact selected expression. Ordinary
dictionary forms and nouns have no extra conjugation disclosure.

Token spans use the existing source code-point offsets. Automatic explanation
does not cross whitespace, punctuation or another independent predicate. Rules
account for the checked IPADIC split 読ん／じゃ／う as well as its ordinary
auxiliary/non-independent verb splits.

The continuing-action/state and desire additions reuse the existing verb and
i-adjective inflection rules. They add no tokenizer, dictionary, dependency or
service API changes. Regression coverage includes checked IPADIC auxiliary
splits, voiced でる, irregular classes, code-point offsets, exact manual spans
and popup lookup/save behavior. See the
[verification record](ui-testing.md#continuing-actionstate-and-desire-conjugations).
The additional voice/conditional/command rules use the same exact-span checks.
Real tokenizer snapshots and their pinned input-manifest identity are retained in
[`conjugation-fixtures.json`](../apps/desktop/src/features/translation/conjugation-fixtures.json);
see [expanded conjugation verification](ui-testing.md#expanded-conjugation-explanations).

### Grammar references

The rule code and short explanations are written for YomiMado; no third-party
rule table, grammar dataset, model or source text is bundled. Grammar facts were
checked against the author's published explanations in Tae Kim's guide:

- [Negative verbs](https://guidetojapanese.org/learn/grammar/negativeverbs)
- [Past tense](https://guidetojapanese.org/learn/grammar/past)
- [Adjectives](https://guidetojapanese.org/learn/grammar/adjectives)
- [Polite forms and stems](https://guidetojapanese.org/learn/grammar/polite)
- [てしまう and casual contractions](https://guidetojapanese.org/learn/grammar/unintended)
- [ている, enduring states and conversational contractions](https://guidetojapanese.org/learn/grammar/teform)
- [たい and desire forms](https://guidetojapanese.org/learn/grammar/desire)
- [Potential forms](https://guidetojapanese.org/learn/grammar/potential)
- [Causative, passive and respectful uses](https://guidetojapanese.org/learn/grammar/causepass)
- [ば and たら conditionals](https://guidetojapanese.org/learn/grammar/conditionals)
- [Command forms](https://guidetojapanese.org/learn/grammar/requests)

Earlier implementation diaries and rollout attempts remain in
[Git history](https://github.com/chonnakanch/yomimado/tree/a5f7ebc/docs).
Follow [documentation maintenance](../AGENTS.md#documentation-maintenance) when
updating this plan.
