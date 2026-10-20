import { expect, it } from "vitest";
import type { TextToken } from "../../lib/ocr-types";
import { explainConjugation } from "./conjugation";

const ichidan = "動詞 / 自立 / 一段 / 連用形";
const godan = "動詞 / 自立 / 五段・ラ行 / 連用形";
const adjective = "形容詞 / 自立 / 形容詞・アウオ段 / 連用形";
function token(
  surface: string,
  dictionaryForm: string,
  partOfSpeech: string,
  start = 0,
): TextToken {
  return {
    surface,
    dictionaryForm,
    partOfSpeech,
    start,
    end: start + Array.from(surface).length,
    reading: "",
  };
}

it.each([
  ["食べた", "食べる", ichidan, ["食べる"]],
  ["食べない", "食べる", ichidan, ["食べる"]],
  ["食べなかった", "食べる", ichidan, ["食べない", "食べる"]],
  ["食べます", "食べる", ichidan, ["食べる"]],
  ["食べました", "食べる", ichidan, ["食べます", "食べる"]],
  ["食べません", "食べる", ichidan, ["食べます", "食べる"]],
  ["食べませんでした", "食べる", ichidan, ["食べません", "食べます", "食べる"]],
  ["買った", "買う", "動詞 / 自立 / 五段・ワ行促音便", ["買う"]],
  ["書いた", "書く", "動詞 / 自立 / 五段・カ行イ音便", ["書く"]],
  ["泳いだ", "泳ぐ", "動詞 / 自立 / 五段・ガ行", ["泳ぐ"]],
  ["話した", "話す", "動詞 / 自立 / 五段・サ行", ["話す"]],
  ["待った", "待つ", "動詞 / 自立 / 五段・タ行", ["待つ"]],
  ["死んだ", "死ぬ", "動詞 / 自立 / 五段・ナ行", ["死ぬ"]],
  ["遊んだ", "遊ぶ", "動詞 / 自立 / 五段・バ行", ["遊ぶ"]],
  ["読んだ", "読む", "動詞 / 自立 / 五段・マ行", ["読む"]],
  ["帰った", "帰る", godan, ["帰る"]],
  ["帰らなかった", "帰る", godan, ["帰らない", "帰る"]],
  ["帰りました", "帰る", godan, ["帰ります", "帰る"]],
  ["行った", "行く", "動詞 / 自立 / 五段・カ行促音便", ["行く"]],
  ["問うた", "問う", "動詞 / 自立 / 五段・ワ行ウ音便", ["問う"]],
  ["した", "する", "動詞 / 自立 / サ変・スル", ["する"]],
  [
    "しませんでした",
    "する",
    "動詞 / 自立 / サ変・スル",
    ["しません", "します", "する"],
  ],
  ["来なかった", "来る", "動詞 / 自立 / カ変・来ル", ["来ない", "来る"]],
  ["きました", "くる", "動詞 / 自立 / カ変・クル", ["きます", "くる"]],
  ["なかった", "ある", godan, ["ない", "ある"]],
  ["高かった", "高い", adjective, ["高い"]],
  ["高くない", "高い", adjective, ["高い"]],
  ["高くなかったです", "高い", adjective, ["高くなかった", "高くない", "高い"]],
  ["高いです", "高い", adjective, ["高い"]],
  ["よかった", "いい", adjective, ["いい"]],
  ["可愛かった", "可愛い", adjective, ["可愛い"]],
  ["食べちゃう", "食べる", ichidan, ["食べてしまう", "食べる"]],
  [
    "食べちゃった",
    "食べる",
    ichidan,
    ["食べてしまった", "食べてしまう", "食べる"],
  ],
  ["読んじゃう", "読む", "動詞 / 自立 / 五段・マ行", ["読んでしまう", "読む"]],
  [
    "読んじゃった",
    "読む",
    "動詞 / 自立 / 五段・マ行",
    ["読んでしまった", "読んでしまう", "読む"],
  ],
  [
    "行っちゃった",
    "行く",
    "動詞 / 自立 / 五段・カ行促音便",
    ["行ってしまった", "行ってしまう", "行く"],
  ],
] as const)(
  "explains %s using the analyzed class of %s",
  (surface, base, pos, chain) => {
    const selected = token(surface, base, pos);
    const analysis = explainConjugation(surface, [selected], selected, false);
    expect(analysis?.status).toBe("supported");
    if (analysis?.status !== "supported")
      throw new Error("Expected supported analysis");
    expect(analysis.dictionaryForm).toBe(base);
    expect(analysis.steps.map((item) => item.to)).toEqual(chain);
    expect(analysis.steps[0].from).toBe(surface);
    expect(
      analysis.steps.every(
        (item, index) =>
          index === 0 || item.from === analysis.steps[index - 1].to,
      ),
    ).toBe(true);
  },
);

// These splits and POS strings were checked with the pinned Lindera/IPADIC provider.
const politeTokens = [
  token("食べ", "食べる", ichidan),
  token("まし", "ます", "助動詞 / 特殊・マス", 2),
  token("た", "た", "助動詞 / 特殊・タ", 4),
];
it("combines the exact adjacent auxiliary tokens when clicking the verb stem", () => {
  expect(
    explainConjugation("食べました。", politeTokens, politeTokens[0], false),
  ).toMatchObject({
    status: "supported",
    surface: "食べました",
    label: "Polite past",
  });
});
it("uses a complete manual span and keeps partial selections explicit", () => {
  const manual = token("食べました", "食べました", "");
  expect(
    explainConjugation("食べました。", politeTokens, manual, true),
  ).toMatchObject({ status: "supported", dictionaryForm: "食べる" });
  expect(
    explainConjugation(
      "食べました。",
      politeTokens,
      { ...manual, surface: "食べま", end: 3 },
      true,
    )?.status,
  ).toBe("unsupported");
  expect(
    explainConjugation(
      "食べました。",
      politeTokens,
      token("べました", "べました", "", 1),
      true,
    )?.status,
  ).toBe("unsupported");
});
it("expands a manga contraction without choosing its contextual meaning", () => {
  const tokens = [
    token("食べ", "食べる", ichidan),
    token("ちゃっ", "ちゃう", "動詞 / 非自立 / 五段・ワ行促音便", 2),
    token("た", "た", "助動詞 / 特殊・タ", 5),
  ];
  const result = explainConjugation("食べちゃった！", tokens, tokens[0], false);
  expect(result).toMatchObject({
    status: "supported",
    surface: "食べちゃった",
  });
  if (result?.status === "supported")
    expect(result.note).toContain("depends on context");
});
it("handles IPADIC's separate interjection token in 読んじゃう", () => {
  const tokens = [
    token("読ん", "読む", "動詞 / 自立 / 五段・マ行"),
    token("じゃ", "じゃ", "助詞 / 接続助詞", 2),
    token("う", "う", "感動詞", 4),
  ];
  expect(
    explainConjugation("読んじゃう", tokens, tokens[0], false),
  ).toMatchObject({
    status: "supported",
    surface: "読んじゃう",
    dictionaryForm: "読む",
  });
});
it("keeps multi-word manual predicates outside the supported slice", () => {
  const tokens = [
    token("勉強", "勉強", "名詞 / サ変接続"),
    token("した", "する", "動詞 / 自立 / サ変・スル", 2),
  ];
  expect(
    explainConjugation(
      "勉強した",
      tokens,
      token("勉強した", "勉強した", ""),
      true,
    )?.status,
  ).toBe("unsupported");
});
it.each([
  "食べられた",
  "食べさせられました",
  "食べたい",
  "食べれば",
  "食べろ",
  "食べてる",
  "食べていました",
  "食べちゃいました",
])("does not mislabel unsupported %s as a simpler ending", (surface) => {
  const tokens = [
    token("食べ", "食べる", ichidan),
    token(surface.slice(2), "られる", "動詞 / 接尾 / 一段", 2),
  ];
  expect(explainConjugation(surface, tokens, tokens[0], false)?.status).toBe(
    "unsupported",
  );
});
it("does not guess a verb class from る or explain nouns as adjectives", () => {
  for (const pos of ["動詞", ichidan]) {
    const selected = token("帰った", "帰る", pos);
    expect(
      explainConjugation(selected.surface, [selected], selected, false)?.status,
    ).toBe("unsupported");
  }
  const noun = token("きれい", "きれい", "名詞 / 形容動詞語幹");
  expect(explainConjugation(noun.surface, [noun], noun, false)).toBeNull();
});
it("does not cross whitespace, punctuation or an independent next verb", () => {
  for (const source of ["食べ ました", "食べ、ました"]) {
    const tokens = [politeTokens[0], token("ました", "ます", "助動詞", 3)];
    expect(explainConjugation(source, tokens, tokens[0], false)).toMatchObject({
      status: "unsupported",
      surface: "食べ",
    });
  }
  const tokens = [
    token("食べた", "食べる", ichidan),
    token("見る", "見る", ichidan, 3),
  ];
  expect(
    explainConjugation("食べた見る", tokens, tokens[0], false),
  ).toMatchObject({ status: "supported", surface: "食べた" });
});
it("preserves source code-point offsets and rejects mismatched OCR text", () => {
  const tokens = politeTokens.map((item) => ({
    ...item,
    start: item.start + 1,
    end: item.end + 1,
  }));
  expect(
    explainConjugation("𠮷食べました。", tokens, tokens[0], false),
  ).toMatchObject({ status: "supported", surface: "食べました" });
  expect(
    explainConjugation("𠮷食へました。", tokens, tokens[0], false)?.status,
  ).toBe("unsupported");
});
it("leaves dictionary forms alone and needs analysis for manual inflections", () => {
  const selected = token("食べる", "食べる", ichidan);
  expect(
    explainConjugation(selected.surface, [selected], selected, false),
  ).toBeNull();
  const manual = token("食べました", "食べました", "");
  expect(explainConjugation(manual.surface, [], manual, true)?.status).toBe(
    "unsupported",
  );
});
