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
  ["食べている", "食べる", ichidan, ["食べる"]],
  ["食べていた", "食べる", ichidan, ["食べている", "食べる"]],
  ["食べていない", "食べる", ichidan, ["食べている", "食べる"]],
  [
    "食べていなかった",
    "食べる",
    ichidan,
    ["食べていない", "食べている", "食べる"],
  ],
  ["食べています", "食べる", ichidan, ["食べている", "食べる"]],
  [
    "食べていました",
    "食べる",
    ichidan,
    ["食べています", "食べている", "食べる"],
  ],
  [
    "食べていません",
    "食べる",
    ichidan,
    ["食べています", "食べている", "食べる"],
  ],
  [
    "食べていませんでした",
    "食べる",
    ichidan,
    ["食べていません", "食べています", "食べている", "食べる"],
  ],
  ["食べてる", "食べる", ichidan, ["食べている", "食べる"]],
  ["食べてた", "食べる", ichidan, ["食べていた", "食べている", "食べる"]],
  ["食べてない", "食べる", ichidan, ["食べていない", "食べている", "食べる"]],
  [
    "食べてなかった",
    "食べる",
    ichidan,
    ["食べていなかった", "食べていない", "食べている", "食べる"],
  ],
  ["食べてます", "食べる", ichidan, ["食べています", "食べている", "食べる"]],
  [
    "食べてました",
    "食べる",
    ichidan,
    ["食べていました", "食べています", "食べている", "食べる"],
  ],
  [
    "食べてません",
    "食べる",
    ichidan,
    ["食べていません", "食べています", "食べている", "食べる"],
  ],
  [
    "食べてませんでした",
    "食べる",
    ichidan,
    [
      "食べていませんでした",
      "食べていません",
      "食べています",
      "食べている",
      "食べる",
    ],
  ],
  ["読んでる", "読む", "動詞 / 自立 / 五段・マ行", ["読んでいる", "読む"]],
  [
    "泳いでた",
    "泳ぐ",
    "動詞 / 自立 / 五段・ガ行",
    ["泳いでいた", "泳いでいる", "泳ぐ"],
  ],
  [
    "行ってる",
    "行く",
    "動詞 / 自立 / 五段・カ行促音便",
    ["行っている", "行く"],
  ],
  [
    "問うてる",
    "問う",
    "動詞 / 自立 / 五段・ワ行ウ音便",
    ["問うている", "問う"],
  ],
  ["来てる", "来る", "動詞 / 自立 / カ変・来ル", ["来ている", "来る"]],
  ["きてる", "くる", "動詞 / 自立 / カ変・クル", ["きている", "くる"]],
  ["してる", "する", "動詞 / 自立 / サ変・スル", ["している", "する"]],
  ["食べたい", "食べる", ichidan, ["食べる"]],
  ["食べたかった", "食べる", ichidan, ["食べたい", "食べる"]],
  ["食べたくない", "食べる", ichidan, ["食べたい", "食べる"]],
  [
    "食べたくなかった",
    "食べる",
    ichidan,
    ["食べたくない", "食べたい", "食べる"],
  ],
  ["食べたいです", "食べる", ichidan, ["食べたい", "食べる"]],
  [
    "食べたかったです",
    "食べる",
    ichidan,
    ["食べたかった", "食べたい", "食べる"],
  ],
  [
    "食べたくないです",
    "食べる",
    ichidan,
    ["食べたくない", "食べたい", "食べる"],
  ],
  [
    "食べたくなかったです",
    "食べる",
    ichidan,
    ["食べたくなかった", "食べたくない", "食べたい", "食べる"],
  ],
  ["買いたい", "買う", "動詞 / 自立 / 五段・ワ行促音便", ["買う"]],
  ["帰りたい", "帰る", godan, ["帰る"]],
  ["したい", "する", "動詞 / 自立 / サ変・スル", ["する"]],
  ["来たかった", "来る", "動詞 / 自立 / カ変・来ル", ["来たい", "来る"]],
  ["きたくない", "くる", "動詞 / 自立 / カ変・クル", ["きたい", "くる"]],
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

// Representative suffix splits checked with pinned Lindera 6.0.0/IPADIC.
const particle = "助詞 / 接続助詞";
const auxiliaryVerb = "動詞 / 非自立 / 一段";
const auxiliary = "助動詞";
it.each([
  [
    "食べている",
    [
      ["て", "て", particle],
      ["いる", "いる", auxiliaryVerb],
    ],
  ],
  ["食べてる", [["てる", "てる", auxiliaryVerb]]],
  [
    "食べてた",
    [
      ["て", "てる", auxiliaryVerb],
      ["た", "た", auxiliary],
    ],
  ],
  [
    "食べてない",
    [
      ["て", "てる", auxiliaryVerb],
      ["ない", "ない", auxiliary],
    ],
  ],
  [
    "食べてなかった",
    [
      ["て", "てる", auxiliaryVerb],
      ["なかっ", "ない", auxiliary],
      ["た", "た", auxiliary],
    ],
  ],
  [
    "食べていました",
    [
      ["て", "て", particle],
      ["い", "いる", auxiliaryVerb],
      ["まし", "ます", auxiliary],
      ["た", "た", auxiliary],
    ],
  ],
  [
    "食べてませんでした",
    [
      ["て", "て", particle],
      ["ませ", "ます", auxiliary],
      ["ん", "ん", auxiliary],
      ["でし", "です", auxiliary],
      ["た", "た", auxiliary],
    ],
  ],
  ["食べたい", [["たい", "たい", auxiliary]]],
  [
    "食べたかった",
    [
      ["たかっ", "たい", auxiliary],
      ["た", "た", auxiliary],
    ],
  ],
  [
    "食べたくない",
    [
      ["たく", "たい", auxiliary],
      ["ない", "ない", auxiliary],
    ],
  ],
  [
    "食べたくなかったです",
    [
      ["たく", "たい", auxiliary],
      ["なかっ", "ない", auxiliary],
      ["た", "た", auxiliary],
      ["です", "です", auxiliary],
    ],
  ],
] as const)(
  "explains the real auxiliary splits of %s on click and manual selection",
  (surface, suffixes) => {
    const tokens = [token("食べ", "食べる", ichidan)];
    for (const [part, base, pos] of suffixes) {
      tokens.push(token(part, base, pos, tokens[tokens.length - 1].end));
    }
    // A supplementary-plane character before the phrase exercises code-point spans.
    const source = `𠮷、${surface}よ。`;
    const offsetTokens = tokens.map((part) => ({
      ...part,
      start: part.start + 2,
      end: part.end + 2,
    }));
    offsetTokens.push(
      token("よ", "よ", "助詞 / 終助詞", 2 + Array.from(surface).length),
    );
    const manual = token(surface, surface, "", 2);
    const automatic = explainConjugation(
      source,
      offsetTokens,
      offsetTokens[0],
      false,
    );
    expect(automatic).toMatchObject({
      status: "supported",
      surface,
      dictionaryForm: "食べる",
    });
    expect(explainConjugation(source, offsetTokens, manual, true)).toEqual(
      automatic,
    );
    if (automatic?.status === "supported")
      expect(automatic.note).toContain("depends on context");
    expect(
      explainConjugation(
        source,
        offsetTokens,
        { ...manual, surface: surface.slice(1), start: 3 },
        true,
      )?.status,
    ).toBe("unsupported");
    expect(
      explainConjugation(
        source.replace("食べ", "食へ"),
        offsetTokens,
        manual,
        true,
      )?.status,
    ).toBe("unsupported");
  },
);

it("expands the voiced でる contraction and stops at an independent next predicate", () => {
  const tokens = [
    token("読ん", "読む", "動詞 / 自立 / 五段・マ行 / 連用タ接続"),
    token("でる", "でる", auxiliaryVerb, 2),
    token("見る", "見る", ichidan, 4),
  ];
  expect(
    explainConjugation("読んでる見る", tokens, tokens[0], false),
  ).toMatchObject({
    status: "supported",
    surface: "読んでる",
    dictionaryForm: "読む",
    steps: [
      { from: "読んでる", to: "読んでいる" },
      { from: "読んでいる", to: "読む" },
    ],
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
  "食べさせられました",
  "食べちゃいました",
  "食べていて",
  "食べていたい",
  "食べてしまっている",
  "食べたがっている",
  "食べたくて",
  "食べたくありません",
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
  for (const source of [
    "食べ ました",
    "食べ、ました",
    "食べ てる",
    "食べ、たい",
  ]) {
    const tokens = [
      politeTokens[0],
      token(source.slice(3), "ます", "助動詞", 3),
    ];
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
