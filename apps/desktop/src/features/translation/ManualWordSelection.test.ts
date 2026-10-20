import { expect, it } from "vitest";
import { selectionToken } from "./ManualWordSelection";

it("converts native UTF-16 selection offsets to original Unicode code points", () => {
  const source = "🙂 𠮷野の生徒会長。";
  const start = source.indexOf("𠮷");
  const end = source.indexOf("。");
  expect(selectionToken(source, start, end)).toEqual({
    surface: "𠮷野の生徒会長",
    dictionaryForm: "𠮷野の生徒会長",
    reading: "",
    partOfSpeech: "",
    start: 2,
    end: 9,
  });
});

it("trims edge whitespace and preserves the original text and offsets across normalized line endings", () => {
  const source = "🙂\r\n \t生徒\r\n会長 \r終";
  const displayed = source.replace(/\r\n?/g, "\n");
  expect(selectionToken(source, 2, displayed.indexOf("終"))).toEqual({
    surface: "生徒\r\n会長",
    dictionaryForm: "生徒\r\n会長",
    reading: "",
    partOfSpeech: "",
    start: 5,
    end: 11,
  });
});

it("rejects empty, invalid and split-surrogate selections", () => {
  for (const [start, end] of [
    [0, 0],
    [-1, 2],
    [0, 99],
    [2, 1],
    [0.5, 2],
    [0, NaN],
    [1, 2],
    [0, 1],
    [2, 3],
  ]) {
    expect(selectionToken("𠮷 学", start, end)).toBeNull();
  }
});
