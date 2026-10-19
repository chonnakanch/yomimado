# Conjugation explanations (development source)

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

## Supported slice

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

## Grammar references and verification

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
