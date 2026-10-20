// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "../../App";
import {
  listVocabularyWords,
  deleteVocabularyWord,
} from "../../lib/vocabulary-client";
import { listSavedSentences } from "../../lib/sentence-client";

vi.mock("../../lib/vocabulary-client", () => ({
  listVocabularyWords: vi.fn(),
  deleteVocabularyWord: vi.fn(),
}));
vi.mock("../../lib/sentence-client", () => ({
  listSavedSentences: vi.fn(),
  deleteSavedSentence: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

const words = [
  {
    id: 3,
    surface: "学校",
    reading: "ガッコウ",
    dictionaryForm: "学校",
    meanings: ["school"],
    sourceText: "学校で勉強する。",
    createdAt: "2026-10-20T00:00:00Z",
  },
  {
    id: 2,
    surface: "食べました",
    reading: "タベマシタ",
    dictionaryForm: "食べる",
    meanings: ["to eat"],
    sourceText: "パンを食べました。",
    createdAt: "2026-10-19T00:00:00Z",
  },
  {
    id: 1,
    surface: "猫",
    reading: "ねこ",
    dictionaryForm: "猫",
    meanings: [],
    sourceText: "",
    createdAt: "2026-10-18T00:00:00Z",
  },
];
const sentences = [
  {
    id: 2,
    sourceText: "学校に行こう。",
    translatedText: "Let's go to school.",
    createdAt: words[0].createdAt,
  },
  {
    id: 1,
    sourceText: "また明日。",
    translatedText: null,
    createdAt: words[1].createdAt,
  },
];
let container: HTMLDivElement;
let root: Root;
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
  window.history.replaceState({}, "", "/?view=saved");
  vi.mocked(listVocabularyWords).mockResolvedValue(words);
  vi.mocked(listSavedSentences).mockResolvedValue(sentences);
  vi.mocked(deleteVocabularyWord).mockResolvedValue(undefined);
  vi.stubGlobal("fetch", vi.fn());
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});
async function open() {
  await act(async () => root.render(<App />));
}
function panel(kind = "words") {
  return container.querySelector<HTMLElement>(`#saved-panel-${kind}`)!;
}
async function search(query: string, kind = "words") {
  const input = panel(kind).querySelector<HTMLInputElement>(
    'input[type="search"]',
  )!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!.call(input, query);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  return input;
}
async function click(selector: string) {
  await act(async () =>
    container.querySelector<HTMLButtonElement>(selector)!.click(),
  );
}
function headwords() {
  return Array.from(
    panel().querySelectorAll(".library-word strong"),
    (node) => node.textContent,
  );
}

it("filters readings, base forms, meanings and source text without new network calls or reordering", async () => {
  await open();
  await search("がっこう");
  expect(headwords()).toEqual(["学校"]);
  expect(panel().textContent).toContain("1 of 3 words");
  await search("食べる EAT");
  expect(headwords()).toEqual(["食べました"]);
  await search("勉強");
  expect(headwords()).toEqual(["学校"]);
  await search("");
  expect(headwords()).toEqual(["学校", "食べました", "猫"]);
  expect(listVocabularyWords).toHaveBeenCalledTimes(1);
  expect(fetch).not.toHaveBeenCalled();
});

it("distinguishes no matches from an empty library and clears search with focus restored", async () => {
  await open();
  const input = await search("unknown");
  expect(panel().textContent).toContain("No matching words");
  expect(panel().textContent).not.toContain("No saved words yet");
  await click(".library-no-results button");
  expect(document.activeElement).toBe(input);
  expect(headwords()).toHaveLength(3);
  await search("unknown");
  await click('[aria-label="Clear words search"]');
  expect(input.value).toBe("");
  expect(document.activeElement).toBe(input);
});

it("keeps word and sentence queries independent across tabs and reopening", async () => {
  await open();
  await search("SCHOOL");
  await click("#saved-tab-sentences");
  await search("明日", "sentences");
  expect(panel("sentences").querySelectorAll(".library-row")).toHaveLength(1);
  expect(panel("sentences").textContent).toContain("また明日。");
  await search("SCHOOL", "sentences");
  expect(panel("sentences").textContent).toContain("学校に行こう。");
  await click("#saved-tab-words");
  expect(headwords()).toEqual(["学校"]);
  expect(panel().querySelector("input")!.value).toBe("SCHOOL");
  await act(async () => root.unmount());
  root = createRoot(container);
  await open();
  expect(headwords()).toEqual(["学校"]);
  await click("#saved-tab-sentences");
  expect(panel("sentences").querySelector("input")!.value).toBe("SCHOOL");
});

it("refreshes the saved data without clearing the query and keeps results after a failed refresh", async () => {
  await open();
  await search("school");
  vi.mocked(listVocabularyWords).mockRejectedValueOnce(
    new Error("Library unavailable"),
  );
  await click("#saved-panel-words [data-refresh]");
  expect(panel().textContent).toContain("Library unavailable");
  expect(headwords()).toEqual(["学校"]);
  expect(panel().querySelector("input")!.value).toBe("school");
  vi.mocked(listVocabularyWords).mockResolvedValueOnce([words[2]]);
  await click("#saved-panel-words [data-refresh]");
  expect(panel().textContent).toContain("No matching words");
  expect(panel().textContent).toContain("0 of 1 words");
});

it("removes only the confirmed filtered entry and keeps unrelated saved words", async () => {
  vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));
  await open();
  await search("school");
  await click('[aria-label="Remove 学校"]');
  expect(deleteVocabularyWord).toHaveBeenCalledExactlyOnceWith(3);
  expect(panel().textContent).toContain("0 of 2 words");
  await search("");
  expect(headwords()).toEqual(["食べました", "猫"]);
});

it("keeps search usable when local storage is blocked", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  await open();
  await search("school");
  expect(headwords()).toEqual(["学校"]);
});

it("does not clear an active Japanese composition with Escape", async () => {
  await open();
  const input = await search("がっこう");
  await act(async () =>
    input.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Escape",
        isComposing: true,
        bubbles: true,
      }),
    ),
  );
  expect(input.value).toBe("がっこう");
  await act(async () =>
    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    ),
  );
  expect(input.value).toBe("");
});
