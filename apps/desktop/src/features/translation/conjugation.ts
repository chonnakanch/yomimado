import type { TextToken } from "../../lib/ocr-types";

export interface ConjugationStep {
  from: string;
  to: string;
  explanation: string;
}
export type ConjugationAnalysis =
  | {
      status: "supported";
      surface: string;
      dictionaryForm: string;
      label: string;
      steps: ConjugationStep[];
      note?: string;
    }
  | { status: "unsupported"; surface: string; reason: string };

interface Form {
  surface: string;
  label: string;
  steps: ConjugationStep[];
  note?: string;
}
const step = (
  from: string,
  to: string,
  explanation: string,
): ConjugationStep => ({ from, to, explanation });
const isPredicate = (token: TextToken) =>
  /^(動詞|形容詞)(?:\s*\/|$)/.test(token.partOfSpeech);
const isContinuation = (token: TextToken) =>
  /^助動詞(?:\s*\/|$)/.test(token.partOfSpeech) ||
  (/^動詞\s*\//.test(token.partOfSpeech) &&
    /非自立|接尾/.test(token.partOfSpeech)) ||
  (/^助詞\s*\//.test(token.partOfSpeech) &&
    token.partOfSpeech.includes("接続助詞") &&
    ["て", "で", "じゃ", "ば"].includes(token.surface));

function adjectiveForms(base: string): Form[] {
  const result: Form[] = [];
  const add = (
    surface: string,
    label: string,
    steps: ConjugationStep[],
    note?: string,
  ) => result.push({ surface, label, steps, note });
  const prefix = base.slice(0, -1);
  // いい uses よい's stem. Other lexical exceptions stay outside this slice.
  const stem = base === "いい" ? "よ" : prefix;
  const negative = `${stem}くない`,
    past = `${stem}かった`,
    negativePast = `${stem}くなかった`;
  const plain = [
    {
      surface: past,
      label: "Adjective past",
      steps: [
        step(past, base, "かった marks the past form of an i-adjective."),
      ],
    },
    {
      surface: negative,
      label: "Adjective negative",
      steps: [step(negative, base, "くない makes an i-adjective negative.")],
    },
    {
      surface: negativePast,
      label: "Adjective negative past",
      steps: [
        step(negativePast, negative, "なかった is the past form of ない."),
        step(negative, base, "くない makes an i-adjective negative."),
      ],
    },
  ];
  for (const form of plain) {
    result.push(form);
    add(`${form.surface}です`, `Polite ${form.label.toLowerCase()}`, [
      step(
        `${form.surface}です`,
        form.surface,
        "です adds politeness; the adjective carries the tense and negation.",
      ),
      ...form.steps,
    ]);
  }
  add(`${base}です`, "Polite adjective", [
    step(`${base}です`, base, "です adds politeness to the i-adjective."),
  ]);
  add(`${stem}ければ`, "Adjective conditional · ば", [
    step(
      `${stem}ければ`,
      base,
      "ければ gives an i-adjective an if-condition form.",
    ),
  ]);
  add(`${stem}くなければ`, "Adjective negative conditional · ば", [
    step(
      `${stem}くなければ`,
      negative,
      "なければ makes the negative an if-condition.",
    ),
    ...plain[1].steps,
  ]);
  add(`${past}ら`, "Adjective conditional · たら", [
    step(
      `${past}ら`,
      past,
      "ら after the past form creates a condition; this does not by itself place the sentence in the past.",
    ),
    ...plain[0].steps,
  ]);
  add(`${negativePast}ら`, "Adjective negative conditional · たら", [
    step(
      `${negativePast}ら`,
      negativePast,
      "ら after the negative past form creates a negative condition.",
    ),
    ...plain[2].steps,
  ]);
  return result;
}

function verbForms(
  base: string,
  stem: string,
  negative: string,
  past: string,
): Form[] {
  const result: Form[] = [];
  const add = (surface: string, label: string, steps: ConjugationStep[]) =>
    result.push({ surface, label, steps });
  const polite = `${stem}ます`,
    politePast = `${stem}ました`,
    politeNegative = `${stem}ません`,
    politeNegativePast = `${stem}ませんでした`;
  const negativePast = `${negative.slice(0, -1)}かった`;
  const politeStep = step(
    polite,
    base,
    "ます marks a polite non-past verb form.",
  );
  const negativeStep = step(
    negative,
    base,
    "ない marks the plain negative verb form.",
  );
  add(past, "Plain past", [
    step(
      past,
      base,
      "た／だ marks the plain past form. The verb class determines the stem change.",
    ),
  ]);
  add(negative, "Plain negative", [negativeStep]);
  add(negativePast, "Plain negative past", [
    step(negativePast, negative, "なかった is the past form of ない."),
    negativeStep,
  ]);
  add(polite, "Polite non-past", [politeStep]);
  add(politePast, "Polite past", [
    step(politePast, polite, "ました is the past form of polite ます."),
    politeStep,
  ]);
  add(politeNegative, "Polite negative", [
    step(politeNegative, polite, "ません is the negative form of polite ます."),
    politeStep,
  ]);
  add(politeNegativePast, "Polite negative past", [
    step(
      politeNegativePast,
      politeNegative,
      "ませんでした marks the past of polite negative ません.",
    ),
    step(politeNegative, polite, "ません is the negative form of polite ます."),
    politeStep,
  ]);
  return result;
}

function forms(base: string, pos: string): Form[] {
  const end = base.slice(-1),
    prefix = base.slice(0, -1);
  if (pos.startsWith("形容詞") && end === "い") return adjectiveForms(base);
  if (!pos.startsWith("動詞")) return [];
  let stem: string, negative: string, past: string, te: string;
  let conditional: string,
    commands: string[],
    passive: string,
    causative: string;
  let passiveLabel = "Passive / honorific";
  if (pos.includes("サ変") && base.endsWith("する")) {
    const root = base.slice(0, -2);
    stem = `${root}し`;
    negative = `${root}しない`;
    past = `${root}した`;
    te = `${root}して`;
    conditional = `${root}すれば`;
    commands = [`${root}しろ`, `${root}せよ`];
    passive = `${root}される`;
    causative = `${root}させる`;
  } else if (pos.includes("カ変") && ["来る", "くる"].includes(base)) {
    stem = base === "来る" ? "来" : "き";
    negative = base === "来る" ? "来ない" : "こない";
    past = `${stem}た`;
    te = `${stem}て`;
    conditional = base === "来る" ? "来れば" : "くれば";
    commands = [base === "来る" ? "来い" : "こい"];
    passive = base === "来る" ? "来られる" : "こられる";
    causative = base === "来る" ? "来させる" : "こさせる";
    passiveLabel = "Potential / passive / honorific";
  } else if (pos.includes("一段") && end === "る") {
    stem = prefix;
    negative = `${stem}ない`;
    past = `${stem}た`;
    te = `${stem}て`;
    conditional = `${prefix}れば`;
    commands = ["くれる", "呉れる"].includes(base)
      ? [prefix]
      : [`${prefix}ろ`, `${prefix}よ`];
    passive = `${prefix}られる`;
    causative = `${prefix}させる`;
    passiveLabel = "Potential / passive / honorific";
  } else if (pos.includes("五段") && !pos.includes("特殊")) {
    const endings: Record<string, [string, string, string, string]> = {
      う: ["い", "わ", "った", "え"],
      く: ["き", "か", "いた", "け"],
      ぐ: ["ぎ", "が", "いだ", "げ"],
      す: ["し", "さ", "した", "せ"],
      つ: ["ち", "た", "った", "て"],
      ぬ: ["に", "な", "んだ", "ね"],
      ぶ: ["び", "ば", "んだ", "べ"],
      む: ["み", "ま", "んだ", "め"],
      る: ["り", "ら", "った", "れ"],
    };
    const ending = endings[end];
    if (!ending) return [];
    stem = prefix + ending[0];
    negative = ["ある", "有る", "在る"].includes(base)
      ? "ない"
      : `${prefix}${ending[1]}ない`;
    past =
      prefix +
      (end === "く" && pos.includes("促音便")
        ? "った"
        : end === "う" && pos.includes("ウ音便")
          ? "うた"
          : ending[2]);
    te = past.slice(0, -1) + (past.endsWith("だ") ? "で" : "て");
    conditional = `${prefix}${ending[3]}ば`;
    commands = [`${prefix}${ending[3]}`];
    passive = `${prefix}${ending[1]}れる`;
    causative = `${prefix}${ending[1]}せる`;
  } else return [];

  const result = verbForms(base, stem, negative, past);
  const add = (
    surface: string,
    label: string,
    steps: ConjugationStep[],
    note?: string,
  ) => result.push({ surface, label, steps, note });

  const conditionalNote =
    "This describes the condition's form, not a translation of the sentence or its result.";
  add(
    conditional,
    "Conditional · ば",
    [
      step(
        conditional,
        base,
        "ば attaches to the verb's conditional stem to express an if-condition.",
      ),
    ],
    conditionalNote,
  );
  add(
    `${past}ら`,
    "Conditional · たら",
    [
      step(
        `${past}ら`,
        past,
        "ら after the past form expresses if or when; the condition need not describe a past event.",
      ),
      ...result[0].steps,
    ],
    conditionalNote,
  );
  const negativePast = `${negative.slice(0, -1)}かった`;
  add(
    `${negative.slice(0, -1)}ければ`,
    "Negative conditional · ば",
    [
      step(
        `${negative.slice(0, -1)}ければ`,
        negative,
        "なければ makes the negative an if-condition.",
      ),
      ...result[1].steps,
    ],
    conditionalNote,
  );
  add(
    `${negativePast}ら`,
    "Negative conditional · たら",
    [
      step(
        `${negativePast}ら`,
        negativePast,
        "ら after the negative past form creates a negative condition.",
      ),
      ...result[2].steps,
    ],
    conditionalNote,
  );
  // A bare e-row surface can also be a conditional stem. Require IPADIC's
  // imperative feature before presenting it as a command.
  if (pos.includes("命令"))
    for (const command of commands)
      add(
        command,
        "Command",
        [
          step(
            command,
            base,
            "The analyzed imperative form gives a direct command.",
          ),
        ],
        "Direct commands can sound forceful. Tone and context determine their effect.",
      );

  const derived = (
    form: string,
    label: string,
    explanation: string,
    note: string,
  ) => {
    const stem = form.slice(0, -1);
    const derivation = step(form, base, explanation);
    for (const variant of [
      { surface: form, label: "", steps: [] },
      ...verbForms(form, stem, `${stem}ない`, `${stem}た`),
    ])
      add(
        variant.surface,
        variant.label ? `${label} · ${variant.label.toLowerCase()}` : label,
        [...variant.steps, derivation],
        note,
      );
  };
  derived(
    passive,
    passiveLabel,
    passiveLabel.startsWith("Potential")
      ? "られる can express ability, passive voice or respectful speech with this analyzed verb class."
      : "れる can express passive voice or respectful speech with this analyzed verb class.",
    "The form alone cannot choose between these interpretations; the intended meaning depends on context.",
  );
  derived(
    causative,
    "Causative",
    "せる／させる expresses causing or allowing someone to perform the action.",
    "Making and letting share this form; who causes or allows the action depends on context.",
  );

  // Compose only the explicitly supported auxiliary families, without generating
  // arbitrary auxiliary chains. The full source span must still match exactly.
  const continuing = `${te}いる`;
  const continuingStep = step(
    continuing,
    base,
    "て／で + いる describes a continuing action or state using the verb's て-form.",
  );
  for (const form of [
    { surface: continuing, label: "Plain non-past", steps: [] },
    ...verbForms(continuing, `${te}い`, `${te}いない`, `${te}いた`),
  ]) {
    const steps = [...form.steps, continuingStep];
    const note =
      "An ongoing action, repeated activity or resulting state depends on context; this is not a sentence translation.";
    add(
      form.surface,
      `Continuing action/state · ${form.label.toLowerCase()}`,
      steps,
      note,
    );
    const contracted = te + form.surface.slice(te.length + 1);
    add(
      contracted,
      `Casual continuing action/state · ${form.label.toLowerCase()}`,
      [
        step(
          contracted,
          form.surface,
          "Conversational てる／でる drops the い in ている／でいる, including in inflected forms.",
        ),
        ...steps,
      ],
      note,
    );
  }

  const desire = `${stem}たい`;
  const desireStep = step(
    desire,
    base,
    "たい attaches to the verb's ます stem to express a wish to do the action; it conjugates like an i-adjective.",
  );
  for (const form of [
    { surface: desire, label: "Desire", steps: [] },
    ...adjectiveForms(desire),
  ]) {
    add(
      form.surface,
      form.label.replace(/adjective/i, "desire"),
      [...form.steps, desireStep],
      "Who wants the action depends on context; this is not a sentence translation.",
    );
  }

  const contracted = te.slice(0, -1) + (te.endsWith("で") ? "じゃ" : "ちゃ");
  const expanded = `${te}しまう`,
    expandedPast = `${te}しまった`;
  const completionStep = step(
    expanded,
    base,
    "て／で + しまう adds completion or an unintended-result nuance to the verb.",
  );
  const note =
    "Completion, regret or an unintended action depends on context; this is not a sentence translation.";
  add(
    `${contracted}う`,
    "Casual てしまう contraction",
    [
      step(
        `${contracted}う`,
        expanded,
        "ちゃう／じゃう is a casual contraction of てしまう／でしまう.",
      ),
      completionStep,
    ],
    note,
  );
  add(
    `${contracted}った`,
    "Casual contraction + past",
    [
      step(
        `${contracted}った`,
        expandedPast,
        "ちゃった／じゃった expands to てしまった／でしまった.",
      ),
      step(expandedPast, expanded, "しまった is the past form of しまう."),
      completionStep,
    ],
    note,
  );
  return result;
}

/** Uses existing tokenizer classes and exact source spans, never a suffix-only base guess. */
export function explainConjugation(
  source: string,
  tokens: TextToken[],
  selected: TextToken,
  manual: boolean,
): ConjugationAnalysis | null {
  const characters = Array.from(source);
  const first = tokens.findIndex((token) => token.start === selected.start);
  const head = tokens[first];
  const unsupported = (
    surface: string,
    reason: string,
  ): ConjugationAnalysis => ({ status: "unsupported", surface, reason });
  if (!head || !isPredicate(head)) {
    return manual &&
      (!head ||
        tokens.some(
          (token) =>
            token.start >= selected.start &&
            token.end <= selected.end &&
            isPredicate(token),
        ))
      ? unsupported(
          selected.surface,
          "Select a complete verb or i-adjective starting at a token boundary. Word analysis must be available.",
        )
      : null;
  }
  let end = head.end;
  for (let index = first + 1; index < tokens.length; index++) {
    const next = tokens[index];
    // IPADIC can split 読んじゃう into 読ん / じゃ / う (interjection).
    // Admit that exact adjacent split; the full generated form must still match.
    const contractedU =
      tokens[index - 1].surface === "じゃ" &&
      next.surface === "う" &&
      next.partOfSpeech.startsWith("感動詞");
    if (next.start !== end || (!isContinuation(next) && !contractedU)) break;
    end = next.end;
  }
  if (manual) end = selected.end;
  const surface = characters.slice(head.start, end).join("");
  if (
    characters.slice(selected.start, selected.end).join("") !==
      selected.surface ||
    (manual && !tokens.some((token) => token.end === end)) ||
    tokens
      .slice(first)
      .some(
        (token) =>
          token.start < end &&
          characters.slice(token.start, token.end).join("") !== token.surface,
      )
  ) {
    return unsupported(
      selected.surface,
      "The selection does not match complete analyzed tokens. Adjust it and try again.",
    );
  }
  if (surface === head.dictionaryForm) return null;
  const matches = forms(head.dictionaryForm, head.partOfSpeech).filter(
    (form) => form.surface === surface,
  );
  if (matches.length !== 1)
    return unsupported(
      surface,
      "This form is not covered by the local conjugation rules yet. Dictionary lookup is still available.",
    );
  return {
    status: "supported",
    dictionaryForm: head.dictionaryForm,
    ...matches[0],
  };
}
