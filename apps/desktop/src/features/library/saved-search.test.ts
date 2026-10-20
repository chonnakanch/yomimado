import { expect, it } from "vitest";
import {
  matchesSavedWord,
  matchesSavedSentence,
  normalizeSavedSearch,
} from "./saved-search";

const word = {
  id: 1,
  surface: "食べました",
  reading: "タベマシタ",
  dictionaryForm: "食べる",
  meanings: ["to eat", "to live on"],
  sourceText: "一緒に昼ご飯を食べました。",
  createdAt: "2026-10-20T00:00:00Z",
};

it.each([
  "食べました",
  "たべました",
  "ﾀﾍﾞﾏｼﾀ",
  "食べる",
  "EAT",
  "昼ご飯",
  "食べる eat",
  "  eat   live  ",
  "",
  "　",
])("matches a saved word using %s without changing its fields", (query) => {
  const before = structuredClone(word);
  expect(matchesSavedWord(word, query)).toBe(true);
  expect(word).toEqual(before);
});

it.each(["school", "eat missing", "1", "2026-10-20"])(
  "does not match absent terms or metadata: %s",
  (query) => {
    expect(matchesSavedWord(word, query)).toBe(false);
  },
);

it("normalizes width, combining dakuten and kana while preserving kanji", () => {
  expect(normalizeSavedSearch("ｶﾞｯｺｳ ガッコウ ＳＣＨＯＯＬ 学校")).toBe(
    "がっこう がっこう school 学校",
  );
});

it("searches saved Japanese and English sentences, including entries without translation", () => {
  const sentence = {
    id: 1,
    sourceText: "またアシタ。",
    translatedText: "See you tomorrow.",
    createdAt: word.createdAt,
  };
  expect(matchesSavedSentence(sentence, "あした TOMORROW")).toBe(true);
  expect(
    matchesSavedSentence({ ...sentence, translatedText: null }, "あした"),
  ).toBe(true);
  expect(
    matchesSavedSentence({ ...sentence, translatedText: null }, "tomorrow"),
  ).toBe(false);
});
