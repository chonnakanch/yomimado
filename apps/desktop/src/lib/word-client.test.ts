import { afterEach, expect, it, vi } from "vitest";
import { requestWord } from "./word-client";

const token = {
  surface: "今度",
  dictionaryForm: "今度",
  reading: "コンド",
  start: 0,
  end: 2,
  partOfSpeech: "名詞",
};

afterEach(() => vi.unstubAllGlobals());

it("requests combined-word senses using the selected token", async () => {
  const entries = [
    {
      expression: "今度",
      reading: "こんど",
      senses: [{ glosses: ["this time", "now"] }],
      match: "surface",
      readingMatch: true,
      common: true,
    },
  ];
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ entries })));
  vi.stubGlobal("fetch", fetch);
  expect(await requestWord(token)).toEqual(entries);
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
    surface: "今度",
    dictionaryForm: "今度",
    reading: "コンド",
  });
});

it("rejects malformed word responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          entries: [
            { expression: "今度", reading: "こんど", senses: "this time" },
          ],
        }),
      ),
    ),
  );
  await expect(requestWord(token)).rejects.toThrow("invalid data");
});
