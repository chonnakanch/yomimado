import { afterEach, expect, it, vi } from "vitest";
import { requestTokenization } from "./tokenization-client";

afterEach(() => vi.unstubAllGlobals());

it("preserves the untrimmed source text and checks token offsets", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        sourceText: " 学校。",
        tokens: [
          {
            surface: "学校",
            reading: "ガッコウ",
            dictionaryForm: "学校",
            start: 1,
            end: 3,
            partOfSpeech: "名詞",
          },
          {
            surface: "。",
            reading: "。",
            dictionaryForm: "。",
            start: 3,
            end: 4,
            partOfSpeech: "補助記号",
          },
        ],
      }),
      { status: 200 },
    ),
  );
  vi.stubGlobal("fetch", fetch);

  const tokens = await requestTokenization(" 学校。");
  expect(tokens[0].reading).toBe("ガッコウ");
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ text: " 学校。" });
});

it("rejects tokens that do not point into the original OCR text", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          sourceText: "学校",
          tokens: [
            {
              surface: "学校",
              reading: "ガッコウ",
              dictionaryForm: "学校",
              start: 1,
              end: 3,
              partOfSpeech: "名詞",
            },
          ],
        }),
        { status: 200 },
      ),
    ),
  );
  await expect(requestTokenization("学校")).rejects.toThrow(
    "invalid token offsets",
  );
});

it("uses Unicode code-point offsets even when an emoji precedes a token", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          sourceText: "🙂学校",
          tokens: [
            {
              surface: "学校",
              reading: "ガッコウ",
              dictionaryForm: "学校",
              start: 1,
              end: 3,
              partOfSpeech: "名詞",
            },
          ],
        }),
        { status: 200 },
      ),
    ),
  );
  await expect(requestTokenization("🙂学校")).resolves.toHaveLength(1);
});
