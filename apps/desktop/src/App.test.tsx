// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { App } from "./App";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.mocked(invoke).mockResolvedValue(undefined);
  window.localStorage.clear();
  window.history.replaceState({}, "", "/");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.mocked(invoke).mockReset();
});

it("opens Scan & OCR by default and leaves capture on the toolbar", async () => {
  await act(async () => root.render(<App />));
  expect(
    container
      .querySelector("#settings-tab-scan")
      ?.getAttribute("aria-selected"),
  ).toBe("true");
  expect(container.querySelector(".main-actions")).toBeNull();
  expect(invoke).not.toHaveBeenCalledWith("show_auto_scanner");
  expect(container.textContent).toContain(
    "Whole Screen finds manga pages on the target monitor before OCR",
  );
});

it("routes Sources directly to attribution and packaged notices", async () => {
  window.history.replaceState({}, "", "/?view=sources");
  await act(async () => root.render(<App />));
  expect(container.querySelector("h1")?.textContent).toBe("Sources & licenses");
  expect(container.querySelector(".settings-window")).toBeNull();
  expect(container.querySelector(".saved-library")).toBeNull();
  expect(container.textContent).toContain("JMdict and KANJIDIC2");
  expect(container.textContent).toContain("Electronic Dictionary Research");
  expect(container.textContent).toContain("ocr/notices");
  expect(
    container.querySelector(
      'a[href="https://www.edrdg.org/edrdg/licence.html"]',
    ),
  ).not.toBeNull();
  expect(invoke).not.toHaveBeenCalled();
});

it("shows saved words and removes one only after confirmation", async () => {
  const word = {
    id: 4,
    surface: "今日",
    reading: "きょう",
    dictionaryForm: "今日",
    meanings: ["today"],
    sourceText: "今日はいい日だ。",
    createdAt: "2026-09-28T12:00:00+00:00",
  };
  const fetch = vi.fn((_url: string, options?: RequestInit) => {
    if (options?.method === "DELETE")
      return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(new Response(JSON.stringify({ words: [word] })));
  });
  vi.stubGlobal("fetch", fetch);
  const confirm = vi.fn().mockReturnValue(false);
  vi.stubGlobal("confirm", confirm);

  window.history.replaceState({}, "", "/?view=saved");
  await act(async () => root.render(<App />));
  expect(container.querySelector(".settings-window")).toBeNull();
  expect(
    container.querySelector('nav[aria-label="Library and settings"]'),
  ).toBeNull();
  expect(container.textContent).toContain("今日");
  expect(container.textContent).toContain("today");
  expect(container.textContent).toContain("今日はいい日だ。");

  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('[aria-label="Remove 今日"]')!
      .click();
  });
  expect(confirm).toHaveBeenCalled();
  expect(fetch).toHaveBeenCalledTimes(1);

  confirm.mockReturnValue(true);
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('[aria-label="Remove 今日"]')!
      .click();
  });
  expect(fetch.mock.calls[1][1]).toEqual({
    method: "DELETE",
    headers: { "x-yomimado-client": "desktop" },
  });
  expect(container.textContent).toContain("No saved words yet");
});

it("shows saved sentences and removes one only after confirmation", async () => {
  const sentence = {
    id: 3,
    sourceText: "今日はいい日だ。",
    translatedText: "It's a good day.",
    createdAt: "2026-09-28T12:00:00+00:00",
  };
  const fetch = vi.fn((url: string, options?: RequestInit) => {
    if (options?.method === "DELETE")
      return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(
      new Response(
        JSON.stringify(
          url.endsWith("/vocabulary")
            ? { words: [] }
            : { sentences: [sentence] },
        ),
      ),
    );
  });
  vi.stubGlobal("fetch", fetch);
  const confirm = vi.fn().mockReturnValue(false);
  vi.stubGlobal("confirm", confirm);

  window.history.replaceState({}, "", "/?view=saved");
  await act(async () => root.render(<App />));
  expect(container.querySelector(".settings-window")).toBeNull();
  expect(
    container.querySelector('nav[aria-label="Library and settings"]'),
  ).toBeNull();
  await act(async () =>
    container.querySelector<HTMLButtonElement>("#saved-tab-sentences")!.click(),
  );
  expect(container.textContent).toContain("今日はいい日だ。");
  expect(container.textContent).toContain("It's a good day.");

  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(
        '[aria-label="Remove saved sentence 3"]',
      )!
      .click();
  });
  expect(confirm).toHaveBeenCalled();
  expect(fetch).toHaveBeenCalledTimes(2);

  confirm.mockReturnValue(true);
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(
        '[aria-label="Remove saved sentence 3"]',
      )!
      .click();
  });
  expect(fetch.mock.calls[2][1]).toEqual({
    method: "DELETE",
    headers: { "x-yomimado-client": "desktop" },
  });
  expect(container.textContent).toContain("No saved sentences yet");
});

it("opens the existing saved-word view when requested by the toolbar", async () => {
  window.history.replaceState({}, "", "/?view=words");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify({ words: [] }))),
  );
  await act(async () => root.render(<App />));
  expect(
    container.querySelector<HTMLDivElement>("#saved-panel-words")?.hidden,
  ).toBe(false);
  expect(container.textContent).toContain("No saved words yet");
  window.history.replaceState({}, "", "/");
});

it("opens the grouped library and switches panels using keyboard tabs", async () => {
  window.history.replaceState({}, "", "/?view=saved");
  const fetch = vi.fn((url: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          url.endsWith("/vocabulary") ? { words: [] } : { sentences: [] },
        ),
      ),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await act(async () => root.render(<App />));
  const words = container.querySelector<HTMLButtonElement>("#saved-tab-words")!;
  const sentences = container.querySelector<HTMLButtonElement>(
    "#saved-tab-sentences",
  )!;
  expect(
    container.querySelector('[role="tablist"]')?.getAttribute("aria-label"),
  ).toBe("Saved collections");
  expect(container.querySelector(".main-actions")).toBeNull();
  expect(document.activeElement).toBe(words);
  expect(words.getAttribute("aria-selected")).toBe("true");
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () =>
    words.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(sentences);
  expect(sentences.tabIndex).toBe(0);
  expect(words.tabIndex).toBe(-1);
  expect(sentences.getAttribute("aria-selected")).toBe("true");
  expect(
    container.querySelector<HTMLElement>("#saved-panel-words")!.hidden,
  ).toBe(true);
  expect(
    container.querySelector<HTMLElement>("#saved-panel-sentences")!.hidden,
  ).toBe(false);
  expect(fetch.mock.calls[1][0]).toContain("/sentences");
  await act(async () =>
    sentences.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Home", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(words);
  expect(fetch.mock.calls[2][0]).toContain("/vocabulary");
  await act(async () =>
    words.dispatchEvent(
      new KeyboardEvent("keydown", { key: "End", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(sentences);
  await act(async () =>
    sentences.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(words);
});

it("preserves independent collection errors and refreshes when returning to a collection", async () => {
  window.history.replaceState({}, "", "/?view=saved");
  const fetch = vi.fn((url: string) =>
    Promise.resolve(
      url.endsWith("/vocabulary")
        ? new Response(JSON.stringify({ detail: "Words unavailable" }), {
            status: 503,
          })
        : new Response(JSON.stringify({ sentences: [] })),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await act(async () => root.render(<App />));
  const click = async (label: string) =>
    act(async () =>
      Array.from(container.querySelectorAll<HTMLButtonElement>("button"))
        .find((item) => item.textContent === label)!
        .click(),
    );
  expect(container.querySelector("#saved-panel-words")?.textContent).toContain(
    "Words unavailable",
  );
  await click("Sentences");
  expect(
    container.querySelector("#saved-panel-sentences")?.textContent,
  ).toContain("No saved sentences yet");
  expect(
    container.querySelector("#saved-panel-sentences")?.textContent,
  ).not.toContain("Words unavailable");
  await click("Words");
  await click("Sentences");
  expect(
    container
      .querySelector<HTMLButtonElement>("#saved-tab-sentences")!
      .getAttribute("aria-selected"),
  ).toBe("true");
  expect(
    fetch.mock.calls.filter(([url]) => url.endsWith("/sentences")),
  ).toHaveLength(2);
});

it("keeps the latest collection response when switching back before an old request finishes", async () => {
  window.history.replaceState({}, "", "/?view=saved");
  let finishOld!: (response: Response) => void;
  let wordCalls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/sentences"))
        return Promise.resolve(new Response(JSON.stringify({ sentences: [] })));
      wordCalls++;
      if (wordCalls === 1)
        return new Promise<Response>((resolve) => {
          finishOld = resolve;
        });
      return Promise.resolve(new Response(JSON.stringify({ words: [] })));
    }),
  );
  await act(async () => root.render(<App />));
  await act(async () =>
    container.querySelector<HTMLButtonElement>("#saved-tab-sentences")!.click(),
  );
  await act(async () =>
    container.querySelector<HTMLButtonElement>("#saved-tab-words")!.click(),
  );
  expect(container.querySelector("#saved-panel-words")?.textContent).toContain(
    "No saved words yet",
  );
  await act(async () =>
    finishOld(
      new Response(JSON.stringify({ detail: "Old request failed" }), {
        status: 503,
      }),
    ),
  );
  expect(
    container.querySelector("#saved-panel-words")?.textContent,
  ).not.toContain("Old request failed");
  expect(container.querySelector("#saved-panel-words")?.textContent).toContain(
    "No saved words yet",
  );
});

const libraryWords = [
  {
    id: 9,
    surface: "学校",
    reading: "ガッコウ",
    dictionaryForm: "学校",
    meanings: ["school"],
    sourceText: "学校に行きます。\n一緒に勉強しましょう。",
    createdAt: "2026-10-14T00:00:00+00:00",
  },
  {
    id: 4,
    surface: "猫",
    reading: "ねこ",
    dictionaryForm: "猫",
    meanings: [],
    sourceText: "",
    createdAt: "legacy unknown date",
  },
];
const librarySentences = [
  {
    id: 7,
    sourceText: "今日はいい天気ですね。",
    translatedText: "It's a fine day today.",
    createdAt: "2026-10-14T00:00:00+00:00",
  },
  {
    id: 2,
    sourceText: "一緒に日本語を勉強しましょう。",
    translatedText: null,
    createdAt: "2026-10-13T00:00:00+00:00",
  },
];
function libraryResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status });
}
function pendingResponse() {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
async function openLibrary(tab = "saved") {
  window.history.replaceState({}, "", `/?view=${tab}`);
  await act(async () => root.render(<App />));
}

it("keeps stored word order, meanings and attribution with context/date collapsed", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(libraryResponse({ words: libraryWords })),
      ),
  );
  await openLibrary();
  const rows = container.querySelectorAll("#saved-panel-words .library-row");
  expect(
    Array.from(rows, (row) => row.querySelector("strong")?.textContent),
  ).toEqual(["学校", "猫"]);
  expect(rows[0].querySelector(".library-reading")?.textContent).toBe(
    "ガッコウ",
  );
  expect(rows[0].textContent).toContain("school");
  expect(rows[0].querySelector<HTMLDetailsElement>("details")!.open).toBe(
    false,
  );
  expect(rows[0].querySelector(".library-source")?.textContent).toBe(
    libraryWords[0].sourceText,
  );
  expect(rows[0].querySelector("time")?.getAttribute("datetime")).toBe(
    "2026-10-14T00:00:00.000Z",
  );
  expect(rows[0].querySelector(".library-attribution")?.textContent).toContain(
    "JMdict (EDRDG) · CC BY-SA 4.0",
  );
  expect(rows[1].textContent).toContain("No dictionary meaning saved.");
  expect(rows[1].textContent).toContain("Saved date unavailable");
  expect(rows[1].textContent).toContain("No source sentence saved.");
  await act(async () => rows[0].querySelector<HTMLElement>("summary")!.click());
  expect(rows[0].querySelector<HTMLDetailsElement>("details")!.open).toBe(true);
});

it("renders Japanese and saved translation without translating unsaved output", async () => {
  const fetch = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(libraryResponse({ sentences: librarySentences })),
    );
  vi.stubGlobal("fetch", fetch);
  await openLibrary("sentences");
  const rows = container.querySelectorAll(
    "#saved-panel-sentences .library-row",
  );
  expect(
    Array.from(
      rows,
      (row) => row.querySelector(".library-sentence")?.textContent,
    ),
  ).toEqual(librarySentences.map((sentence) => sentence.sourceText));
  expect(rows[0].querySelector('[lang="en"]')?.textContent).toBe(
    librarySentences[0].translatedText,
  );
  expect(rows[1].textContent).toContain("No translation saved.");
  expect(rows[0].querySelector<HTMLDetailsElement>("details")!.open).toBe(
    false,
  );
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toContain("/sentences");
});

it("prevents duplicate removal and ignores an old refresh while restoring focus to the next row", async () => {
  const oldList = pendingResponse(),
    deletion = pendingResponse();
  let lists = 0;
  const fetch = vi.fn((_url: string, options?: RequestInit) => {
    if (options?.method === "DELETE") return deletion.promise;
    lists++;
    return lists === 1
      ? Promise.resolve(libraryResponse({ words: libraryWords }))
      : oldList.promise;
  });
  vi.stubGlobal("fetch", fetch);
  const confirm = vi.fn().mockReturnValue(true);
  vi.stubGlobal("confirm", confirm);
  await openLibrary();
  await act(async () =>
    container
      .querySelector<HTMLButtonElement>("#saved-panel-words [data-refresh]")!
      .click(),
  );
  const remove = container.querySelector<HTMLButtonElement>(
    '[aria-label="Remove 学校"]',
  )!;
  remove.focus();
  await act(async () => {
    remove.click();
    remove.click();
  });
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(
    fetch.mock.calls.filter((call) => call[1]?.method === "DELETE"),
  ).toHaveLength(1);
  expect(
    container.querySelector<HTMLButtonElement>('[aria-label="Remove 猫"]')!
      .disabled,
  ).toBe(true);
  expect(
    container.querySelector<HTMLButtonElement>(
      "#saved-panel-words [data-refresh]",
    )!.disabled,
  ).toBe(true);
  await act(async () => deletion.resolve(new Response(null, { status: 204 })));
  expect(container.querySelector('[aria-label="Remove 学校"]')).toBeNull();
  expect(document.activeElement).toBe(
    container.querySelector('[aria-label="Remove 猫"]'),
  );
  await act(async () =>
    oldList.resolve(libraryResponse({ words: libraryWords })),
  );
  expect(container.querySelector('[aria-label="Remove 学校"]')).toBeNull();
  expect(
    container.querySelectorAll("#saved-panel-words .library-row"),
  ).toHaveLength(1);
});

it("keeps a failed removal beside its row and supports confirmed retry with refresh focus", async () => {
  let deletes = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, options?: RequestInit) => {
      if (options?.method === "DELETE") {
        deletes++;
        return Promise.resolve(
          deletes === 1
            ? libraryResponse({ detail: "Delete failed" }, 503)
            : new Response(null, { status: 204 }),
        );
      }
      return Promise.resolve(libraryResponse({ words: [libraryWords[0]] }));
    }),
  );
  const confirm = vi.fn().mockReturnValue(true);
  vi.stubGlobal("confirm", confirm);
  await openLibrary();
  const remove = container.querySelector<HTMLButtonElement>(
    '[aria-label="Remove 学校"]',
  )!;
  remove.focus();
  await act(async () => remove.click());
  expect(
    container.querySelector('.library-row [role="alert"]')?.textContent,
  ).toContain("Could not remove this word: Delete failed");
  expect(container.querySelectorAll(".library-row")).toHaveLength(1);
  expect(remove.disabled).toBe(false);
  await act(async () => remove.click());
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(container.textContent).toContain("No saved words yet");
  expect(document.activeElement).toBe(
    container.querySelector("#saved-panel-words [data-refresh]"),
  );
});

it("does not steal tab focus when a removal completes in the hidden collection", async () => {
  const deletion = pendingResponse();
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, options?: RequestInit) =>
      options?.method === "DELETE"
        ? deletion.promise
        : Promise.resolve(
            libraryResponse(
              url.endsWith("/vocabulary")
                ? { words: libraryWords }
                : { sentences: librarySentences },
            ),
          ),
    ),
  );
  vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));
  await openLibrary();
  const remove = container.querySelector<HTMLButtonElement>(
    '[aria-label="Remove 学校"]',
  )!;
  remove.focus();
  await act(async () => remove.click());
  const tab = container.querySelector<HTMLButtonElement>(
    "#saved-tab-sentences",
  )!;
  tab.focus();
  await act(async () => tab.click());
  await act(async () => deletion.resolve(new Response(null, { status: 204 })));
  expect(document.activeElement).toBe(tab);
  expect(
    container.querySelector<HTMLElement>("#saved-panel-words")!.hidden,
  ).toBe(true);
});

it("retains existing rows during load failure and retries the current collection", async () => {
  let lists = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      lists++;
      return Promise.resolve(
        lists === 2
          ? libraryResponse({ detail: "List unavailable" }, 503)
          : libraryResponse({ words: libraryWords }),
      );
    }),
  );
  await openLibrary();
  await act(async () =>
    container
      .querySelector<HTMLButtonElement>("#saved-panel-words [data-refresh]")!
      .click(),
  );
  expect(
    container.querySelector('#saved-panel-words [role="alert"]')?.textContent,
  ).toContain("List unavailable");
  expect(
    container.querySelectorAll("#saved-panel-words .library-row"),
  ).toHaveLength(2);
  const retry = Array.from(
    container.querySelectorAll<HTMLButtonElement>("button"),
  ).find((button) => button.textContent === "Retry loading words")!;
  await act(async () => retry.click());
  expect(
    container.querySelector('#saved-panel-words [role="alert"]'),
  ).toBeNull();
  expect(
    container.querySelectorAll("#saved-panel-words .library-row"),
  ).toHaveLength(2);
});
