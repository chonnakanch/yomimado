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
    ["て", "で", "じゃ"].includes(token.surface));

function forms(base: string, pos: string): Form[] {
  const result: Form[] = [];
  const add = (
    surface: string,
    label: string,
    steps: ConjugationStep[],
    note?: string,
  ) => result.push({ surface, label, steps, note });
  const end = base.slice(-1),
    prefix = base.slice(0, -1);
  if (pos.startsWith("形容詞") && end === "い") {
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
    return result;
  }
  if (!pos.startsWith("動詞")) return result;
  let stem: string, negative: string, past: string, te: string;
  if (pos.includes("サ変") && base.endsWith("する")) {
    const root = base.slice(0, -2);
    stem = `${root}し`;
    negative = `${root}しない`;
    past = `${root}した`;
    te = `${root}して`;
  } else if (pos.includes("カ変") && ["来る", "くる"].includes(base)) {
    stem = base === "来る" ? "来" : "き";
    negative = base === "来る" ? "来ない" : "こない";
    past = `${stem}た`;
    te = `${stem}て`;
  } else if (pos.includes("一段") && end === "る") {
    stem = prefix;
    negative = `${stem}ない`;
    past = `${stem}た`;
    te = `${stem}て`;
  } else if (pos.includes("五段") && !pos.includes("特殊")) {
    const endings: Record<string, [string, string, string]> = {
      う: ["い", "わ", "った"],
      く: ["き", "か", "いた"],
      ぐ: ["ぎ", "が", "いだ"],
      す: ["し", "さ", "した"],
      つ: ["ち", "た", "った"],
      ぬ: ["に", "な", "んだ"],
      ぶ: ["び", "ば", "んだ"],
      む: ["み", "ま", "んだ"],
      る: ["り", "ら", "った"],
    };
    const ending = endings[end];
    if (!ending) return result;
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
  } else return result;
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
