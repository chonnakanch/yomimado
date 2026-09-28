import { afterEach, expect, it, vi } from "vitest";
import {
  deleteVocabularyWord,
  listVocabularyWords,
  saveVocabularyWord,
} from "./vocabulary-client";

afterEach(() => vi.unstubAllGlobals());

const saved = {
  id: 7,
  surface: "学校",
  reading: "がっこう",
  dictionaryForm: "学校",
  meanings: ["school"],
  sourceText: "学校に行く。",
  createdAt: "2026-09-28T12:00:00+00:00",
};

it("saves, lists, and removes words through the local service", async () => {
  const fetch = vi.fn((_url: string, options?: RequestInit) => {
    if (options?.method === "POST")
      return Promise.resolve(new Response(JSON.stringify(saved)));
    if (options?.method === "DELETE")
      return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(new Response(JSON.stringify({ words: [saved] })));
  });
  vi.stubGlobal("fetch", fetch);

  expect(await saveVocabularyWord(saved)).toEqual(saved);
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual(saved);
  expect(await listVocabularyWords()).toEqual([saved]);
  await deleteVocabularyWord(7);
  expect(fetch.mock.calls[1][1]).toBeUndefined();
  expect(fetch.mock.calls[2][1]).toEqual({ method: "DELETE" });
});

it("rejects malformed vocabulary responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ words: [{ id: 1 }] }))),
  );
  await expect(listVocabularyWords()).rejects.toThrow("invalid data");
});
