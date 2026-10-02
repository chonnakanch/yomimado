// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TranslationPopup } from "./TranslationPopup";

const invokeMock = vi.hoisted(() => vi.fn(() => Promise.resolve()));

vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ close: vi.fn() }),
}));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  invokeMock.mockClear();
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("resizes to its content when details expand", async () => {
  const placement = {
    screen: { x: 0, y: 0, width: 1920, height: 1080 },
    anchorLeft: 100,
    anchorRight: 200,
    anchorTop: 100,
    scaleFactor: 1,
  };
  const state = encodeURIComponent(
    JSON.stringify({ text: "", demo: true, placement }),
  );
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  let observedResize: (() => void) | undefined;
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        observedResize = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callback(0);
    return 1;
  });
  vi.stubGlobal("cancelAnimationFrame", () => {});
  let contentHeight = 420;
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    () => ({ height: contentHeight }) as DOMRect,
  );

  await act(async () => root.render(<TranslationPopup />));
  expect(invokeMock).toHaveBeenLastCalledWith("resize_translation_popup", {
    placement,
    logicalHeight: 422,
  });
  contentHeight = 710;
  await act(async () => observedResize?.());
  expect(invokeMock).toHaveBeenLastCalledWith("resize_translation_popup", {
    placement,
    logicalHeight: 712,
  });
});

it("shows local word analysis while translating only after a click", async () => {
  const state = encodeURIComponent(
    JSON.stringify({ text: "学校", demo: false }),
  );
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  const fetch = vi.fn((url: string, _options?: RequestInit) => {
    if (url.endsWith("/tokenize")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            sourceText: "学校",
            tokens: [
              {
                surface: "学校",
                reading: "ガッコウ",
                dictionaryForm: "学校",
                start: 0,
                end: 2,
                partOfSpeech: "名詞",
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/word")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            entries: [
              {
                expression: "学校",
                reading: "がっこう",
                senses: [{ glosses: ["school"] }],
                match: "surface",
                readingMatch: true,
                common: true,
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/kanji")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            character: "学",
            onReadings: ["ガク"],
            kunReadings: ["まな.ぶ"],
            meanings: ["study"],
          }),
        ),
      );
    }
    if (url.endsWith("/kanji/examples")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            examples: [
              {
                expression: "学生",
                reading: "がくせい",
                meanings: ["student"],
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/vocabulary")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: 1,
            surface: "学校",
            reading: "がっこう",
            dictionaryForm: "学校",
            meanings: ["school"],
            sourceText: "学校",
            createdAt: "2026-09-28T12:00:00+00:00",
          }),
        ),
      );
    }
    return Promise.resolve(
      new Response(
        JSON.stringify({
          sourceText: "学校",
          translatedText: "School",
          provider: "test-local-model",
          cached: true,
        }),
        { status: 200 },
      ),
    );
  });
  vi.stubGlobal("fetch", fetch);

  await act(async () => root.render(<TranslationPopup />));
  expect(
    (container.querySelector("textarea") as HTMLTextAreaElement).value,
  ).toBe("学校");
  expect(
    container.querySelector('label[for="translation-source"]')?.textContent,
  ).toBe("OCR text");
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(container.textContent).not.toContain("ガッコウ");
  await act(async () => {
    container.querySelector<HTMLButtonElement>(".tokenization-word")!.click();
  });
  expect(container.textContent).toContain("ガッコウ");
  expect(container.textContent).toContain("Base: 学校");
  expect(container.textContent).toContain("POS: 名詞");
  expect(container.textContent).not.toContain("Combined word meaning");
  expect(container.textContent).toContain("school");
  expect(container.querySelectorAll(".kanji-choices button")).toHaveLength(2);
  expect(container.textContent).not.toContain("Meanings: study");
  expect(container.textContent).not.toContain("Example compounds");
  expect(fetch).toHaveBeenCalledTimes(2);
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('[aria-label="Look up kanji 学"]')!
      .click();
  });
  expect(container.textContent).toContain("Meanings: study");
  expect(container.textContent).toContain("On: ガク");
  expect(container.textContent).toContain("Used here in 学校");
  expect(container.textContent).toContain("Example compounds");
  expect(container.textContent).toContain("学生");
  expect(container.textContent).toContain("student");
  expect(fetch.mock.calls[0][0]).toContain("/tokenize");

  await act(async () => {
    container.querySelector<HTMLButtonElement>(".translate-button")!.click();
  });
  expect(fetch).toHaveBeenCalledTimes(5);
  expect(fetch.mock.calls[4][0]).toContain("/translate");
  expect(container.textContent).toContain("School");
  expect(container.textContent).toContain("cached");
  expect(container.textContent).toContain("Save this word");
  expect(fetch).toHaveBeenCalledTimes(5);
  await act(async () => {
    container.querySelector<HTMLButtonElement>(".save-word-button")!.click();
  });
  expect(fetch).toHaveBeenCalledTimes(6);
  expect(fetch.mock.calls[5][0]).toContain("/vocabulary");
  expect(JSON.parse(fetch.mock.calls[5][1]!.body as string)).toEqual({
    surface: "学校",
    reading: "がっこう",
    dictionaryForm: "学校",
    meanings: ["school"],
    sourceText: "学校",
  });
  expect(container.textContent).toContain("Saved");
});

it("saves a sentence without translating and can later include requested translation", async () => {
  const text = "今日はいい日だ。";
  const state = encodeURIComponent(JSON.stringify({ text, demo: false }));
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  const fetch = vi.fn((url: string, options?: RequestInit) => {
    if (url.endsWith("/tokenize"))
      return Promise.resolve(
        new Response(JSON.stringify({ sourceText: text, tokens: [] })),
      );
    if (url.endsWith("/sentences")) {
      const input = JSON.parse(options?.body as string) as {
        sourceText: string;
        translatedText?: string;
      };
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: 1,
            sourceText: input.sourceText,
            translatedText: input.translatedText ?? null,
            createdAt: "2026-09-28T12:00:00+00:00",
          }),
        ),
      );
    }
    if (url.endsWith("/translate"))
      return Promise.resolve(
        new Response(
          JSON.stringify({
            sourceText: text,
            translatedText: "It's a good day.",
            provider: "test-local-model",
            cached: false,
          }),
        ),
      );
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetch);

  await act(async () => root.render(<TranslationPopup />));
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(".sentence-save-actions button")!
      .click();
  });
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls[1][0]).toContain("/sentences");
  expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
    sourceText: text,
  });
  expect(container.textContent).toContain("Sentence saved locally.");

  await act(async () => {
    container.querySelector<HTMLButtonElement>(".translate-button")!.click();
  });
  expect(container.textContent).not.toContain("Sentence saved locally.");
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(".sentence-save-actions button")!
      .click();
  });
  expect(JSON.parse(fetch.mock.calls[3][1]!.body as string)).toEqual({
    sourceText: text,
    translatedText: "It's a good day.",
  });
});

it("keeps punctuation as sentence context but not as selectable words", async () => {
  const text = "今日!?学校";
  const state = encodeURIComponent(JSON.stringify({ text, demo: false }));
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  const tokens = [
    {
      surface: "今日",
      reading: "キョウ",
      dictionaryForm: "今日",
      start: 0,
      end: 2,
      partOfSpeech: "名詞",
    },
    {
      surface: "学校",
      reading: "ガッコウ",
      dictionaryForm: "学校",
      start: 4,
      end: 6,
      partOfSpeech: "名詞",
    },
  ];
  const fetch = vi.fn((url: string, options?: RequestInit) => {
    if (url.endsWith("/tokenize")) {
      return Promise.resolve(
        new Response(JSON.stringify({ sourceText: text, tokens })),
      );
    }
    if (url.endsWith("/word")) {
      return Promise.resolve(new Response(JSON.stringify({ entries: [] })));
    }
    if (url.endsWith("/vocabulary")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: 2,
            surface: "学校",
            reading: "ガッコウ",
            dictionaryForm: "学校",
            meanings: [],
            sourceText: text,
            createdAt: "2026-09-28T12:00:00+00:00",
          }),
        ),
      );
    }
    expect(JSON.parse(options?.body as string)).toEqual({ text });
    return Promise.resolve(
      new Response(
        JSON.stringify({
          sourceText: text,
          translatedText: "Today!? School",
          provider: "test-local-model",
          cached: false,
        }),
      ),
    );
  });
  vi.stubGlobal("fetch", fetch);

  await act(async () => root.render(<TranslationPopup />));
  const words =
    container.querySelectorAll<HTMLButtonElement>(".tokenization-word");
  expect(Array.from(words, (word) => word.textContent)).toEqual([
    "今日",
    "学校",
  ]);
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(text);

  await act(async () => words[1].click());
  expect(container.textContent).toContain("ガッコウ");
  expect(container.textContent).not.toContain("キョウ");

  await act(async () => {
    container.querySelector<HTMLButtonElement>(".translate-button")!.click();
  });
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(container.textContent).toContain("Today!? School");
  await act(async () => {
    container.querySelector<HTMLButtonElement>(".save-word-button")!.click();
  });
  expect(JSON.parse(fetch.mock.calls[3][1]!.body as string)).toEqual({
    surface: "学校",
    reading: "ガッコウ",
    dictionaryForm: "学校",
    meanings: [],
    sourceText: text,
  });
  expect(container.textContent).toContain("Saved without meaning");
});

it("does not treat a demo boundary as recognized text", async () => {
  const state = encodeURIComponent(
    JSON.stringify({ text: "Demo", demo: true }),
  );
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  await act(async () => root.render(<TranslationPopup />));
  expect(
    (container.querySelector("textarea") as HTMLTextAreaElement).value,
  ).toBe("");
  expect(
    container.querySelector<HTMLButtonElement>(".translate-button")!.disabled,
  ).toBe(true);
});
