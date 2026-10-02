import { afterEach, expect, it, vi } from "vitest";
import {
  deleteSavedSentence,
  listSavedSentences,
  saveSentence,
} from "./sentence-client";

afterEach(() => vi.unstubAllGlobals());

const saved = {
  id: 7,
  sourceText: "学校に行く。",
  translatedText: "I go to school.",
  createdAt: "2026-09-28T12:00:00+00:00",
};

it("saves, lists, and removes sentences through the local service", async () => {
  const fetch = vi.fn((_url: string, options?: RequestInit) => {
    if (options?.method === "POST")
      return Promise.resolve(new Response(JSON.stringify(saved)));
    if (options?.method === "DELETE")
      return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(
      new Response(JSON.stringify({ sentences: [saved] })),
    );
  });
  vi.stubGlobal("fetch", fetch);

  expect(await saveSentence(saved)).toEqual(saved);
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual(saved);
  expect(await listSavedSentences()).toEqual([saved]);
  await deleteSavedSentence(7);
  expect(fetch.mock.calls[1][1]).toBeUndefined();
  expect(fetch.mock.calls[2][1]).toEqual({ method: "DELETE" });
});

it("rejects malformed sentence responses", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ sentences: [{ id: 1 }] })),
      ),
  );
  await expect(listSavedSentences()).rejects.toThrow("invalid data");
});
