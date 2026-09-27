// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TranslationPopup } from "./TranslationPopup";

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ close: vi.fn() }),
}));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

it("shows local word analysis while translating only after a click", async () => {
  const state = encodeURIComponent(
    JSON.stringify({ text: "学校", demo: false }),
  );
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  const fetch = vi.fn((url: string) => {
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
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(container.textContent).not.toContain("ガッコウ");
  await act(async () => {
    container.querySelector<HTMLButtonElement>(".tokenization-word")!.click();
  });
  expect(container.textContent).toContain("ガッコウ");
  expect(container.textContent).toContain("Base: 学校");
  expect(container.textContent).toContain("POS: 名詞");
  expect(container.querySelectorAll(".kanji-choices button")).toHaveLength(2);
  expect(fetch).toHaveBeenCalledTimes(1);
  fetch.mockImplementation((url: string) => {
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
    return Promise.resolve(
      new Response(
        JSON.stringify({
          sourceText: "学校",
          translatedText: "School",
          provider: "test-local-model",
          cached: true,
        }),
      ),
    );
  });
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('[aria-label="Look up kanji 学"]')!
      .click();
  });
  expect(container.textContent).toContain("Meanings: study");
  expect(container.textContent).toContain("On: ガク");
  expect(container.textContent).toContain("Used here in 学校");
  expect(fetch.mock.calls[0][0]).toContain("/tokenize");

  await act(async () => {
    container.querySelector<HTMLButtonElement>(".translate-button")!.click();
  });
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(fetch.mock.calls[2][0]).toContain("/translate");
  expect(container.textContent).toContain("School");
  expect(container.textContent).toContain("cached");
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
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(container.textContent).toContain("Today!? School");
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
