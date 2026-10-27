import { expect, it } from "vitest";
import type { TextToken } from "../../lib/ocr-types";
import type { SavedWord } from "../../lib/vocabulary-client";
import { savedWordTokenIndexes } from "./saved-word-highlights";
import conjugationFixtures from "./conjugation-fixtures.json";

it("highlights complete newly supported voice and conditional forms from saved bases", () => {
  for (const text of ["食べられた", "読ませました", "行けば"]) {
    const fixture = conjugationFixtures.cases.find(
      (item) => item.text === text,
    )!;
    expect([
      ...savedWordTokenIndexes(text, fixture.tokens, [
        saved(fixture.dictionaryForm),
      ]),
    ]).toEqual(fixture.tokens.map((_, index) => index));
  }
});

const saved = (dictionaryForm: string): SavedWord => ({
  id: 1,
  surface: dictionaryForm,
  dictionaryForm,
  reading: "",
  meanings: [],
  sourceText: "An earlier sentence",
  createdAt: "2026-10-27T00:00:00Z",
});

function tokens(
  parts: Array<[string, string, string?]>,
  offset = 0,
): TextToken[] {
  return parts.map(([surface, dictionaryForm, partOfSpeech = "名詞"]) => {
    const start = offset;
    offset += Array.from(surface).length;
    return {
      surface,
      dictionaryForm,
      partOfSpeech,
      start,
      end: offset,
      reading: "",
    };
  });
}

it.each([
  ["行く", [["行く", "行く", "動詞 / 自立 / 五段・カ行促音便"]]],
  [
    "行った",
    [
      ["行っ", "行く", "動詞 / 自立 / 五段・カ行促音便"],
      ["た", "た", "助動詞"],
    ],
  ],
  [
    "行きます",
    [
      ["行き", "行く", "動詞 / 自立 / 五段・カ行促音便"],
      ["ます", "ます", "助動詞"],
    ],
  ],
] satisfies Array<[string, Array<[string, string, string?]>]>)(
  "highlights saved 行く throughout %s without saving another context",
  (source, parts) => {
    const analyzed = tokens(parts);
    expect([
      ...savedWordTokenIndexes(source, analyzed, [saved("行く")]),
    ]).toEqual(analyzed.map((_, index) => index));
    expect([...savedWordTokenIndexes(source, analyzed, [])]).toEqual([]);
  },
);

it("keeps literal gaps and Unicode offsets while matching whole manual expressions", () => {
  const source = "😀 取り戻す。取り";
  const analyzed = tokens(
    [
      ["取り", "取る"],
      ["戻す", "戻す"],
      ["。", "。"],
      ["取り", "取る"],
    ],
    2,
  );
  expect([
    ...savedWordTokenIndexes(source, analyzed, [saved("取り戻す")]),
  ]).toEqual([0, 1]);
  expect([...savedWordTokenIndexes(source, analyzed, [saved("戻")])]).toEqual(
    [],
  );
});

it("matches dictionary spelling rather than readings or arbitrary kana variants", () => {
  const analyzed = tokens([
    ["橋", "橋"],
    ["箸", "箸"],
    ["はし", "はし"],
  ]);
  expect([
    ...savedWordTokenIndexes("橋箸はし", analyzed, [saved("橋")]),
  ]).toEqual([0]);
});

it("does not extend a saved verb marker into unsupported auxiliary chains", () => {
  const source = "食べさせられる";
  const analyzed = tokens([
    ["食べ", "食べる", "動詞 / 自立 / 一段"],
    ["させられる", "させられる", "動詞 / 接尾 / 一段"],
  ]);
  expect([
    ...savedWordTokenIndexes(source, analyzed, [saved("食べる")]),
  ]).toEqual([0]);
});
