// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TranslationPopup } from "./TranslationPopup";
import {
  deleteVocabularyWord,
  saveVocabularyWord,
  type SavedWord,
} from "../../lib/vocabulary-client";
import { restoreSavedBackup } from "../../lib/backup-client";
import { vocabularyRevisionKey } from "../../lib/vocabulary-events";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ close: vi.fn() }),
}));

const text = "😀 行った。学校";
const savedWord: SavedWord = {
  id: 1,
  surface: "行く",
  dictionaryForm: "行く",
  reading: "いく",
  meanings: ["to go"],
  sourceText: "明日行く。",
  createdAt: "2026-10-27T00:00:00Z",
};
let container: HTMLDivElement;
let root: Root;
let words: SavedWord[];
let failList: boolean;
let fetchMock: ReturnType<typeof vi.fn>;

function highlighted() {
  return Array.from(container.querySelectorAll(".is-saved-word")).map(
    (node) => node.textContent,
  );
}

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
  words = [savedWord];
  failList = false;
  window.history.replaceState(
    {},
    "",
    `/?mode=translation&state=${encodeURIComponent(JSON.stringify({ text, demo: false }))}`,
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/tokenize"))
      return Response.json({
        sourceText: text,
        tokens: [
          {
            surface: "行っ",
            dictionaryForm: "行く",
            reading: "イッ",
            partOfSpeech: "動詞 / 自立 / 五段・カ行促音便",
            start: 2,
            end: 4,
          },
          {
            surface: "た",
            dictionaryForm: "た",
            reading: "タ",
            partOfSpeech: "助動詞",
            start: 4,
            end: 5,
          },
          {
            surface: "。",
            dictionaryForm: "。",
            reading: "",
            partOfSpeech: "記号",
            start: 5,
            end: 6,
          },
          {
            surface: "学校",
            dictionaryForm: "学校",
            reading: "ガッコウ",
            partOfSpeech: "名詞",
            start: 6,
            end: 8,
          },
        ],
      });
    if (url.endsWith("/word")) return Response.json({ entries: [] });
    if (url.endsWith("/backup/restore")) {
      words = [savedWord];
      return Response.json({
        wordsAdded: 1,
        wordsSkipped: 0,
        sentencesAdded: 0,
        sentencesSkipped: 0,
      });
    }
    if (options?.method === "DELETE") {
      words = [];
      return new Response(null, { status: 204 });
    }
    if (url.endsWith("/vocabulary")) {
      if (options?.method === "POST") {
        words = [savedWord];
        return Response.json(savedWord);
      }
      if (failList)
        return Response.json(
          { detail: "Database unavailable" },
          { status: 500 },
        );
      return Response.json({ words });
    }
    throw new Error(`Unexpected request ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

it("highlights previous saves on open while keeping word lookup and sentence text intact", async () => {
  await act(async () => root.render(<TranslationPopup />));
  expect(highlighted()).toEqual(["行っ", "た"]);
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(text);
  expect(
    container.querySelector('[aria-label="行っ (saved word)"]'),
  ).not.toBeNull();
  expect(
    fetchMock.mock.calls.map(([url]) => new URL(url).pathname).sort(),
  ).toEqual(["/api/v1/tokenize", "/api/v1/vocabulary"]);
  await act(async () =>
    container.querySelector<HTMLButtonElement>(".is-saved-word")!.click(),
  );
  expect(
    container.querySelector('.is-saved-word[aria-pressed="true"]'),
  ).not.toBeNull();
  expect(container.querySelector(".word-definition")).not.toBeNull();
  expect(
    fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
  ).toHaveLength(2);
});

it("updates after successful save, delete and restore without changing sentence saving", async () => {
  words = [];
  await act(async () => root.render(<TranslationPopup />));
  expect(highlighted()).toEqual([]);
  await act(async () => {
    await saveVocabularyWord(savedWord);
  });
  expect(highlighted()).toEqual(["行っ", "た"]);
  await act(async () => {
    await deleteVocabularyWord(1);
  });
  expect(highlighted()).toEqual([]);
  await act(async () => {
    await restoreSavedBackup({ name: "backup.json", contents: "{}" });
  });
  expect(highlighted()).toEqual(["行っ", "た"]);
  expect(
    container.querySelector('[aria-label="Save sentence"]'),
  ).not.toBeNull();
});

it("refreshes for other windows and focus, and recovers from a failed vocabulary read", async () => {
  await act(async () => root.render(<TranslationPopup />));
  words = [];
  await act(async () =>
    window.dispatchEvent(
      new StorageEvent("storage", { key: vocabularyRevisionKey }),
    ),
  );
  expect(highlighted()).toEqual([]);
  words = [savedWord];
  failList = true;
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(highlighted()).toEqual([]);
  expect(container.textContent).toContain("Saved-word highlights unavailable");
  expect(container.querySelectorAll(".tokenization-word")).toHaveLength(3);
  failList = false;
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(highlighted()).toEqual(["行っ", "た"]);
  expect(container.textContent).not.toContain(
    "Saved-word highlights unavailable",
  );
});

it("ignores an older vocabulary response arriving after a newer refresh", async () => {
  let finishOld: (response: Response) => void = () => {};
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementationOnce(
    () =>
      new Promise<Response>((resolve) => {
        finishOld = resolve;
      }),
  );
  // The hook starts the vocabulary read before the tokenization effect.
  await act(async () => root.render(<TranslationPopup />));
  fetchMock.mockImplementation(original);
  words = [];
  await act(async () => window.dispatchEvent(new Event("focus")));
  await act(async () => finishOld(Response.json({ words: [savedWord] })));
  expect(highlighted()).toEqual([]);
});
