import { afterEach, expect, it, vi } from "vitest";
import { requestKanji, requestKanjiExamples } from "./kanji-client";

afterEach(() => vi.unstubAllGlobals());

it("requests one kanji and validates the local response", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        character: "学",
        onReadings: ["ガク"],
        kunReadings: ["まな.ぶ"],
        meanings: ["study"],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  expect(await requestKanji("学")).toEqual({
    character: "学",
    onReadings: ["ガク"],
    kunReadings: ["まな.ぶ"],
    meanings: ["study"],
  });
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ character: "学" });
  await expect(requestKanji("学校")).rejects.toThrow("Select one kanji");
  await expect(requestKanji("あ")).rejects.toThrow("Select one kanji");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("rejects malformed dictionary responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          character: "学",
          onReadings: "ガク",
          kunReadings: [],
          meanings: [],
        }),
      ),
    ),
  );
  await expect(requestKanji("学")).rejects.toThrow("invalid data");
});

it("requests local example compounds and validates their meanings", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        examples: [
          { expression: "学生", reading: "がくせい", meanings: ["student"] },
        ],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  expect(await requestKanjiExamples("学", "学校")).toEqual([
    { expression: "学生", reading: "がくせい", meanings: ["student"] },
  ]);
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
    character: "学",
    excludeWord: "学校",
  });
  await expect(requestKanjiExamples("あ", "学校")).rejects.toThrow(
    "Select one kanji",
  );
});
