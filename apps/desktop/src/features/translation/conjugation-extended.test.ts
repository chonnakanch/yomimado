import { expect, it } from "vitest";
import type { TextToken } from "../../lib/ocr-types";
import fixtures from "./conjugation-fixtures.json";
import { explainConjugation } from "./conjugation";

// Real, synthetic-sentence snapshots from pinned Lindera/IPADIC. Keep lexical
// ambiguities in the fixture instead of assigning a more convenient base.
it.each(fixtures.cases)(
  "uses the actual tokenizer analysis of $text",
  (fixture) => {
    const offset = 2;
    const source = `𠮷、${fixture.text}よ。`;
    const tokens = fixture.tokens.map((token) => ({
      ...token,
      start: token.start + offset,
      end: token.end + offset,
    }));
    tokens.push({
      surface: "よ",
      dictionaryForm: "よ",
      reading: "ヨ",
      partOfSpeech: "助詞 / 終助詞",
      start: Array.from(source).length - 2,
      end: Array.from(source).length - 1,
    });
    const result = explainConjugation(source, tokens, tokens[0], false);
    if (fixture.label === null) {
      expect(result).toBeNull();
      return;
    }
    if (fixture.label === "unsupported") {
      expect(result?.status).toBe("unsupported");
      return;
    }
    expect(result).toMatchObject({
      status: "supported",
      dictionaryForm: fixture.dictionaryForm,
      surface: fixture.text,
      label: fixture.label,
    });
    if (result?.status !== "supported")
      throw new Error("Expected a complete analysis");
    expect(result.steps[0].from).toBe(fixture.text);
    expect(result.steps.at(-1)?.to).toBe(fixture.dictionaryForm);
    result.steps.forEach((step, index) => {
      if (index) expect(step.from).toBe(result.steps[index - 1].to);
    });
    const manual: TextToken = {
      surface: fixture.text,
      dictionaryForm: fixture.text,
      reading: "",
      partOfSpeech: "",
      start: offset,
      end: offset + Array.from(fixture.text).length,
    };
    expect(explainConjugation(source, tokens, manual, true)).toEqual(result);
    expect(
      explainConjugation(
        source,
        tokens,
        { ...manual, surface: manual.surface.slice(1), start: offset + 1 },
        true,
      )?.status,
    ).not.toBe("supported");
    expect(
      explainConjugation(
        source.replace(fixture.text, `猫${fixture.text.slice(1)}`),
        tokens,
        manual,
        true,
      )?.status,
    ).toBe("unsupported");
  },
);

it.each([
  ["買う", "五段・ワ行促音便", "買えば", "買え", "買われる", "買わせる"],
  ["書く", "五段・カ行イ音便", "書けば", "書け", "書かれる", "書かせる"],
  ["泳ぐ", "五段・ガ行", "泳げば", "泳げ", "泳がれる", "泳がせる"],
  ["話す", "五段・サ行", "話せば", "話せ", "話される", "話させる"],
  ["待つ", "五段・タ行", "待てば", "待て", "待たれる", "待たせる"],
  ["死ぬ", "五段・ナ行", "死ねば", "死ね", "死なれる", "死なせる"],
  ["遊ぶ", "五段・バ行", "遊べば", "遊べ", "遊ばれる", "遊ばせる"],
  ["読む", "五段・マ行", "読めば", "読め", "読まれる", "読ませる"],
  ["帰る", "五段・ラ行", "帰れば", "帰れ", "帰られる", "帰らせる"],
])(
  "covers the analyzed godan class of %s",
  (base, verbClass, conditional, command, passive, causative) => {
    // These verify the rule families given a supplied class. Actual IPADIC can
    // choose another lexical analysis for a bare form (retained in fixtures above).
    for (const [surface, label, inflection] of [
      [conditional, "Conditional · ば", "仮定形"],
      [command, "Command", "命令ｅ"],
      [passive, "Passive / honorific", "未然形"],
      [causative, "Causative", "未然形"],
    ]) {
      const token: TextToken = {
        surface,
        dictionaryForm: base,
        reading: "",
        partOfSpeech: `動詞 / 自立 / ${verbClass} / ${inflection}`,
        start: 0,
        end: Array.from(surface).length,
      };
      expect(explainConjugation(surface, [token], token, false)).toMatchObject({
        status: "supported",
        dictionaryForm: base,
        label,
      });
    }
  },
);

it("keeps potential/passive/honorific and make/let meanings explicitly unresolved", () => {
  for (const [text, words] of [
    ["食べられる", ["ability", "passive", "respectful"]],
    ["読まれる", ["passive", "respectful"]],
    ["食べさせる", ["causing", "allowing"]],
  ] as const) {
    const fixture = fixtures.cases.find((item) => item.text === text)!;
    const result = explainConjugation(
      text,
      fixture.tokens,
      fixture.tokens[0],
      false,
    );
    expect(result?.status).toBe("supported");
    if (result?.status !== "supported") throw new Error("Missing analysis");
    expect(result.note).toContain("depends on context");
    for (const word of words)
      expect(result.steps.at(-1)?.explanation).toContain(word);
  }
});

it("requires an analyzed imperative rather than labeling a conditional stem as a command", () => {
  const token: TextToken = {
    surface: "待て",
    dictionaryForm: "待つ",
    reading: "マテ",
    partOfSpeech: "動詞 / 自立 / 五段・タ行 / 仮定形",
    start: 0,
    end: 2,
  };
  expect(explainConjugation("待て", [token], token, false)?.status).toBe(
    "unsupported",
  );
});
