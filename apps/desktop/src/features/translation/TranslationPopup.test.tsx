// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TranslationPopup } from "./TranslationPopup";
import type { TextToken } from "../../lib/ocr-types";
import { hiraganaReading } from "./ClickableSentence";

const invokeMock = vi.hoisted(() => vi.fn(() => Promise.resolve()));

vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ close: vi.fn() }),
}));

let container: HTMLDivElement;
let root: Root;

function button(label: string) {
  const found = Array.from(
    container.querySelectorAll<HTMLButtonElement>("button"),
  ).find(
    (item) =>
      item.textContent?.trim() === label ||
      item.getAttribute("aria-label") === label,
  );
  if (!found) throw new Error(`Button missing: ${label}`);
  return found;
}

async function click(label: string) {
  await act(async () => button(label).click());
}

async function editDraft(text: string) {
  await act(async () => {
    const textarea = container.querySelector<HTMLTextAreaElement>("textarea")!;
    Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      "value",
    )!.set!.call(textarea, text);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

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
  vi.unstubAllEnvs();
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
  let contentHeight = 300;
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    function (this: HTMLElement) {
      return {
        height: this.classList.contains("popup-context") ? 120 : contentHeight,
      } as DOMRect;
    },
  );

  await act(async () => root.render(<TranslationPopup />));
  expect(invokeMock).toHaveBeenLastCalledWith("resize_translation_popup", {
    placement,
    logicalHeight: 422,
    viewQuery: window.location.search.slice(1),
  });
  contentHeight = 590;
  await act(async () => observedResize?.());
  expect(invokeMock).toHaveBeenLastCalledWith("resize_translation_popup", {
    placement,
    logicalHeight: 712,
    viewQuery: window.location.search.slice(1),
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
  expect(container.querySelector("textarea")).toBeNull();
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(
    "学校",
  );
  expect(container.querySelector(".word-definition")).toBeNull();
  expect(container.querySelector(".translation-output")).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(container.textContent).not.toContain("がっこう");
  await act(async () => {
    container.querySelector<HTMLButtonElement>(".tokenization-word")!.click();
  });
  expect(container.textContent).toContain("がっこう");
  expect(container.textContent).toContain("Base form学校");
  expect(container.textContent).toContain("Token POS名詞");
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
  expect(container.textContent).toContain("On’yomiガク");
  expect(container.textContent).toContain("Used here in 学校");
  expect(container.textContent).toContain("Example compounds");
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(container.textContent).not.toContain("学生");
  await click("Example compounds");
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
    button("Save sentence").click();
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
    button("Save sentence").click();
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
  expect(container.textContent).toContain("がっこう");
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

it.each(["success", "error"])(
  "ignores stale translation %s after editing and starting another request",
  async (outcome) => {
    const state = encodeURIComponent(
      JSON.stringify({ text: "学校", demo: false }),
    );
    window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
    const pending: Array<(response: Response) => void> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, options?: RequestInit) => {
        if (url.endsWith("/tokenize")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                sourceText: JSON.parse(options!.body as string).text,
                tokens: [],
              }),
            ),
          );
        }
        return new Promise<Response>((resolve) => pending.push(resolve));
      }),
    );

    await act(async () => root.render(<TranslationPopup />));
    const button =
      container.querySelector<HTMLButtonElement>(".translate-button")!;
    await act(async () => button.click());
    expect(pending).toHaveLength(1);

    await click("Edit OCR text");
    await act(async () => {
      const textarea =
        container.querySelector<HTMLTextAreaElement>("textarea")!;
      Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value",
      )!.set!.call(textarea, "猫");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
    });
    // A draft does not change the applied sentence or invalidate its request.
    expect(button.disabled).toBe(true);
    await click("Apply and analyze");
    expect(container.querySelector(".tokenization-text")?.textContent).toBe(
      "猫",
    );
    expect(button.disabled).toBe(false);
    await act(async () => button.click());
    expect(pending).toHaveLength(2);

    await act(async () =>
      pending[0](
        outcome === "success"
          ? new Response(
              JSON.stringify({
                sourceText: "学校",
                translatedText: "School",
                provider: "test",
                cached: false,
              }),
            )
          : new Response(JSON.stringify({ detail: "Old request failed" }), {
              status: 503,
            }),
      ),
    );
    expect(container.textContent).not.toContain("School");
    expect(container.textContent).not.toContain("Old request failed");
    expect(button.disabled).toBe(true);

    await act(async () =>
      pending[1](
        new Response(
          JSON.stringify({
            sourceText: "猫",
            translatedText: "Cat",
            provider: "test",
            cached: false,
          }),
        ),
      ),
    );
    expect(container.textContent).toContain("Cat");
    expect(button.disabled).toBe(false);
  },
);

it.each([false, true])(
  "retains OCR review guidance and focus return with debug tooltips enabled=%s",
  async (debug) => {
    vi.stubEnv("VITE_CAPTURE_DEBUG", debug ? "1" : "0");
    const query = `?mode=translation&state=${encodeURIComponent(JSON.stringify({ text: "", demo: true, reviewReason: "Check short text", approximate: true }))}`;
    window.history.replaceState({}, "", `/${query}`);
    await act(async () => root.render(<TranslationPopup />));
    const review = container.querySelector(
      '.translation-heading [role="status"]',
    );
    expect(review?.textContent).toContain("Check OCR");
    if (debug)
      expect(review?.getAttribute("title")).toContain(
        "Approximate OCR region. Check short text",
      );
    else expect(review?.getAttribute("title")).toBeNull();
    expect(review?.querySelector(".visually-hidden")?.textContent).toContain(
      "Use Edit OCR text to correct it.",
    );
    expect(
      Array.from(container.querySelectorAll("button")).filter(
        (item) => item.textContent === "Edit OCR text",
      ),
    ).toHaveLength(1);
    // Escape first dismisses the demo editor, then closes the popup.
    await click("Cancel");
    await act(async () =>
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
    );
    expect(invokeMock).toHaveBeenCalledWith("close_translation_popup", {
      returnFocus: true,
      viewQuery: query.slice(1),
    });
    const close = container.querySelector(
      'button[aria-label="Close translation"]',
    )!;
    await act(async () =>
      close.dispatchEvent(
        new MouseEvent("click", { bubbles: true, detail: 1 }),
      ),
    );
    expect(invokeMock).toHaveBeenLastCalledWith("close_translation_popup", {
      returnFocus: false,
      viewQuery: query.slice(1),
    });
  },
);

const schoolToken: TextToken = {
  surface: "学校",
  reading: "ガッコウ",
  dictionaryForm: "学校",
  start: 0,
  end: 2,
  partOfSpeech: "名詞",
};
const schoolEntry = {
  expression: "学校",
  reading: "がっこう",
  senses: [{ glosses: ["school"] }],
  match: "surface",
  readingMatch: true,
  common: true,
};
function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status });
}
function deferred() {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
async function openPopup(text = "学校") {
  window.history.replaceState(
    {},
    "",
    `/?mode=translation&state=${encodeURIComponent(JSON.stringify({ text, demo: false }))}`,
  );
  await act(async () => root.render(<TranslationPopup />));
}
function serviceMock(
  handler?: (
    path: string,
    body: Record<string, string>,
  ) => Response | Promise<Response> | undefined,
) {
  const fetch = vi.fn(async (url: string, options?: RequestInit) => {
    const path = new URL(url).pathname;
    const body = JSON.parse(options!.body as string);
    const custom = handler?.(path, body);
    if (custom) return custom;
    if (path.endsWith("/tokenize"))
      return response({
        sourceText: body.text,
        tokens: body.text === "学校" ? [schoolToken] : [],
      });
    if (path.endsWith("/word")) return response({ entries: [schoolEntry] });
    if (path.endsWith("/kanji"))
      return response({
        character: body.character,
        onReadings: ["ガク"],
        kunReadings: ["まな.ぶ"],
        meanings: ["study"],
      });
    if (path.endsWith("/kanji/examples")) return response({ examples: [] });
    if (path.endsWith("/vocabulary"))
      return response({ ...body, id: 1, createdAt: "2026-10-14T00:00:00Z" });
    if (path.endsWith("/sentences"))
      return response({
        ...body,
        translatedText: body.translatedText ?? null,
        id: 1,
        createdAt: "2026-10-14T00:00:00Z",
      });
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

async function selectText(start: number, end: number) {
  const input = container.querySelector<HTMLTextAreaElement>(
    ".sentence-selection-text",
  )!;
  await act(async () => {
    input.focus();
    input.setSelectionRange(start, end);
    document.dispatchEvent(new Event("selectionchange"));
    input.dispatchEvent(
      new KeyboardEvent("keyup", { key: "Shift", bubbles: true }),
    );
  });
  return input;
}

it("looks up across token boundaries only on request and saves the chosen entry with original context", async () => {
  const source = "彼は生徒会長です。";
  const entry = {
    ...schoolEntry,
    expression: "生徒会長",
    reading: "セイトカイチョウ",
    readingMatch: false,
    senses: [{ glosses: ["student council president"] }],
  };
  const alternate = {
    ...entry,
    expression: "生徒会長別表記",
    reading: "セイトカイチョー",
    senses: [{ glosses: ["alternate meaning"] }],
  };
  const fetch = serviceMock((path) => {
    if (path.endsWith("/tokenize"))
      return response({
        sourceText: source,
        tokens: [
          {
            ...schoolToken,
            surface: "生徒",
            dictionaryForm: "生徒",
            start: 2,
            end: 4,
          },
          {
            ...schoolToken,
            surface: "会長",
            dictionaryForm: "会長",
            start: 4,
            end: 6,
          },
        ],
      });
    if (path.endsWith("/word"))
      return response({ entries: [entry, alternate] });
  });
  await openPopup(source);
  await click("Select text");
  const input = await selectText(2, 6);
  expect(input.readOnly).toBe(false);
  expect(input.getAttribute("aria-readonly")).toBe("true");
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(button("Look up selection").disabled).toBe(false);
  await click("Look up selection");
  expect(
    JSON.parse(
      fetch.mock.calls.find(([url]) => url.endsWith("/word"))![1]!
        .body as string,
    ),
  ).toEqual({ surface: "生徒会長", dictionaryForm: "生徒会長", reading: "" });
  expect(container.querySelector(".selected-word")?.textContent).toBe(
    "生徒会長",
  );
  expect(container.textContent).not.toContain("Reading differs");
  expect(container.querySelector(".word-metadata")).toBeNull();
  const alternative = container.querySelector<HTMLDetailsElement>(
    ".alternative-matches",
  )!;
  await act(async () => {
    alternative.open = true;
    alternative.querySelector<HTMLButtonElement>(".save-word-button")!.click();
  });
  expect(
    JSON.parse(
      fetch.mock.calls.find(([url]) => url.endsWith("/vocabulary"))![1]!
        .body as string,
    ),
  ).toEqual({
    surface: "生徒会長",
    reading: alternate.reading,
    dictionaryForm: alternate.expression,
    meanings: ["alternate meaning"],
    sourceText: source,
  });
  expect(input.value).toBe(source);
  expect([input.selectionStart, input.selectionEnd]).toEqual([2, 6]);
  expect(fetch.mock.calls.some(([url]) => url.endsWith("/translate"))).toBe(
    false,
  );
  await click("Look up kanji 生");
  expect(container.querySelector(".kanji-detail")?.textContent).toContain(
    "Used here in 生徒会長.",
  );
  expect(container.querySelector(".kanji-detail")?.textContent).not.toContain(
    "whole-word reading:",
  );
  await click("Example compounds");
  expect(
    JSON.parse(
      fetch.mock.calls.find(([url]) => url.endsWith("/kanji/examples"))![1]!
        .body as string,
    ),
  ).toEqual({ character: "生", excludeWord: "生徒会長" });
});

it("preserves unmatched selection, allows shrinking inside a token, and restores normal word clicks", async () => {
  const fetch = serviceMock((path, body) =>
    path.endsWith("/word")
      ? response({ entries: body.surface === "学校" ? [] : [schoolEntry] })
      : undefined,
  );
  await openPopup();
  await click("Select text");
  let input = await selectText(0, 2);
  await click("Look up selection");
  expect(container.textContent).toContain("Adjust the selection and try again");
  expect([input.selectionStart, input.selectionEnd]).toEqual([0, 2]);
  input = await selectText(1, 2);
  expect(
    fetch.mock.calls.filter(([url]) => url.endsWith("/word")),
  ).toHaveLength(1);
  await click("Look up selection");
  expect(container.querySelector(".selected-word")?.textContent).toBe("校");
  await click("Back to normal");
  expect(container.querySelector(".sentence-selection-text")).toBeNull();
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(
    "学校",
  );
  await click("学校");
  expect(container.querySelector(".selected-reading")?.textContent).toBe(
    "がっこう",
  );
  expect(container.querySelector(".word-metadata")?.textContent).toContain(
    "Token POS名詞",
  );
});

it("supports manual lookup when tokenization fails and retries a failed selection lookup", async () => {
  let first = true;
  const fetch = serviceMock((path) => {
    if (path.endsWith("/tokenize"))
      return response({ detail: "Tokenizer unavailable" }, 503);
    if (path.endsWith("/word") && first) {
      first = false;
      return response({ detail: "Dictionary unavailable" }, 503);
    }
  });
  await openPopup();
  await click("Select text");
  await selectText(0, 2);
  await click("Look up selection");
  expect(container.textContent).toContain("Dictionary unavailable");
  await click("Retry word lookup");
  expect(container.textContent).toContain("school");
  expect(
    fetch.mock.calls.filter(([url]) => url.endsWith("/tokenize")),
  ).toHaveLength(1);
});

it("rejects blank, punctuation-only and oversized selections before lookup", async () => {
  const text = " \n!?" + "学".repeat(101);
  const fetch = serviceMock();
  await openPopup(text);
  await click("Select text");
  expect(button("Look up selection").disabled).toBe(true);
  await selectText(0, 2);
  expect(button("Look up selection").disabled).toBe(true);
  await selectText(2, 4);
  expect(button("Look up selection").disabled).toBe(true);
  await selectText(4, text.length);
  expect(button("Look up selection").disabled).toBe(true);
  expect(container.textContent).toContain("Select at most 100 characters");
  expect(fetch).toHaveBeenCalledTimes(1);
  await selectText(4, text.length - 1);
  expect(button("Look up selection").disabled).toBe(false);
});

it("ignores stale manual lookup and save completions after a new lookup or OCR correction", async () => {
  const oldLookup = deferred();
  const oldSave = deferred();
  let lookups = 0;
  const fetch = serviceMock((path) => {
    if (path.endsWith("/word") && ++lookups === 1) return oldLookup.promise;
    if (path.endsWith("/vocabulary")) return oldSave.promise;
  });
  await openPopup();
  await click("Select text");
  await selectText(0, 1);
  await click("Look up selection");
  await selectText(0, 2);
  await click("Look up selection");
  await act(async () =>
    oldLookup.resolve(
      response({
        entries: [
          { ...schoolEntry, senses: [{ glosses: ["STALE MANUAL RESULT"] }] },
        ],
      }),
    ),
  );
  expect(container.textContent).not.toContain("STALE MANUAL RESULT");
  expect(container.querySelector(".selected-word")?.textContent).toBe("学校");
  await click("Save this word");
  const payload = JSON.parse(
    fetch.mock.calls.find(([url]) => url.endsWith("/vocabulary"))![1]!
      .body as string,
  );
  await click("Edit OCR text");
  await editDraft("猫");
  await click("Apply and analyze");
  await act(async () =>
    oldSave.resolve(
      response({ ...payload, id: 1, createdAt: "2026-10-19T00:00:00Z" }),
    ),
  );
  expect(container.querySelector(".word-definition")).toBeNull();
  expect(container.textContent).not.toContain("Word saved locally.");
  await click("Select text");
  const input = container.querySelector<HTMLTextAreaElement>(
    ".sentence-selection-text",
  )!;
  expect(input.value).toBe("猫");
  expect(button("Look up selection").disabled).toBe(true);
});

it("exits selection mode on Escape and returns keyboard focus before closing the popup", async () => {
  serviceMock();
  await openPopup();
  await click("Select text");
  expect(document.activeElement).toBe(
    container.querySelector(".sentence-selection-text"),
  );
  await act(async () =>
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
  );
  expect(document.activeElement).toBe(button("Select text"));
  expect(invokeMock).not.toHaveBeenCalledWith(
    "close_translation_popup",
    expect.anything(),
  );
  await act(async () =>
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
  );
  expect(invokeMock).toHaveBeenCalledWith(
    "close_translation_popup",
    expect.anything(),
  );
});

it("keeps native caret navigation while preventing edits to the selection text", async () => {
  const fetch = serviceMock();
  await openPopup();
  await click("Select text");
  const input = await selectText(0, 1);
  expect(input.readOnly).toBe(false);
  expect(document.activeElement).toBe(input);
  for (const key of ["ArrowRight", "ArrowLeft", "Home", "End"]) {
    const event = new KeyboardEvent("keydown", {
      key,
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    await act(async () => input.dispatchEvent(event));
    expect(event.defaultPrevented).toBe(false);
  }
  for (const inputType of [
    "insertText",
    "deleteContentBackward",
    "deleteContentForward",
    "insertFromPaste",
    "insertLineBreak",
    "historyUndo",
    "historyRedo",
  ]) {
    const event = new InputEvent("beforeinput", {
      inputType,
      data: "changed",
      bubbles: true,
      cancelable: true,
    });
    await act(async () => input.dispatchEvent(event));
    expect(event.defaultPrevented).toBe(true);
    expect(input.value).toBe("学校");
  }
  for (const type of ["paste", "cut", "drop"]) {
    const event = new Event(type, { bubbles: true, cancelable: true });
    await act(async () => input.dispatchEvent(event));
    expect(event.defaultPrevented).toBe(true);
  }
  const copy = new Event("copy", { bubbles: true, cancelable: true });
  input.dispatchEvent(copy);
  expect(copy.defaultPrevented).toBe(false);
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      "value",
    )!.set!.call(input, "IME text");
    input.dispatchEvent(
      new InputEvent("input", {
        inputType: "insertCompositionText",
        bubbles: true,
      }),
    );
  });
  expect(input.value).toBe("学校");
  expect([input.selectionStart, input.selectionEnd]).toEqual([0, 1]);
  await click("Look up selection");
  expect(
    JSON.parse(
      fetch.mock.calls.find(([url]) => url.endsWith("/word"))![1]!
        .body as string,
    ),
  ).toEqual({ surface: "学", dictionaryForm: "学", reading: "" });
  expect(
    fetch.mock.calls.filter(([url]) => url.endsWith("/tokenize")),
  ).toHaveLength(1);
});

it("renders source during analysis failure and retries without requesting meanings or translation", async () => {
  const pending = deferred();
  let first = true;
  const fetch = serviceMock((path) => {
    if (path.endsWith("/tokenize") && first) {
      first = false;
      return pending.promise;
    }
  });
  await openPopup();
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(
    "学校",
  );
  expect(container.textContent).toContain("Analyzing words…");
  await act(async () =>
    pending.resolve(response({ detail: "Tokenizer unavailable" }, 503)),
  );
  expect(container.textContent).toContain("Tokenizer unavailable");
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(
    "学校",
  );
  await click("Retry word analysis");
  expect(container.querySelectorAll(".tokenization-word")).toHaveLength(1);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("preserves Unicode gaps and punctuation and displays kana without changing raw readings", async () => {
  const text = "🙂 学校\n!? ありがとう。";
  serviceMock((path) =>
    path.endsWith("/tokenize")
      ? response({
          sourceText: text,
          tokens: [
            { ...schoolToken, start: 2, end: 4 },
            {
              surface: "ありがとう",
              reading: "アリガトウ",
              dictionaryForm: "ありがとう",
              start: 8,
              end: 13,
              partOfSpeech: "感動詞",
            },
          ],
        })
      : undefined,
  );
  await openPopup(text);
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(text);
  const words =
    container.querySelectorAll<HTMLButtonElement>(".tokenization-word");
  expect(words).toHaveLength(2);
  await act(async () => words[1].click());
  expect(container.querySelector(".selected-reading")?.textContent).toBe(
    "ありがとう",
  );
  expect(container.querySelector(".kanji-section")).toBeNull();
  expect(words[1].getAttribute("aria-pressed")).toBe("true");
  expect(hiraganaReading("スーパー・ガッコウ abc ヷ")).toBe(
    "すーぱー・がっこう abc ヷ",
  );
});

it("keeps alternatives collapsed and saves only the chosen entry's raw reading and senses", async () => {
  const alternate = {
    ...schoolEntry,
    expression: "学園",
    reading: "ガクエン",
    senses: [{ glosses: ["academy", "campus"] }],
    match: "dictionaryForm",
    readingMatch: false,
  };
  const fetch = serviceMock((path) =>
    path.endsWith("/word")
      ? response({ entries: [schoolEntry, alternate] })
      : undefined,
  );
  await openPopup();
  await click("学校");
  const details = container.querySelector<HTMLDetailsElement>(
    ".alternative-matches",
  )!;
  expect(details.open).toBe(false);
  expect(details.querySelector("summary")?.textContent).toBe(
    "Alternative dictionary matches (1)",
  );
  await act(async () => {
    details.open = true;
    details.dispatchEvent(new Event("toggle"));
  });
  expect(details.textContent).toContain("Matched base form");
  expect(details.textContent).toContain("がくえん");
  await act(async () =>
    details.querySelector<HTMLButtonElement>(".save-word-button")!.click(),
  );
  const request = fetch.mock.calls.find(([url]) =>
    url.endsWith("/vocabulary"),
  )!;
  expect(JSON.parse(request[1]!.body as string)).toEqual({
    surface: "学校",
    reading: "ガクエン",
    dictionaryForm: "学園",
    meanings: ["academy; campus"],
    sourceText: "学校",
  });
  expect(details.textContent).toContain("Saved locally");
  expect(
    container.querySelector<HTMLButtonElement>(".word-entry .save-word-button")!
      .disabled,
  ).toBe(false);
});

it("retains selected metadata and save without meaning when dictionary lookup fails", async () => {
  serviceMock((path) =>
    path.endsWith("/word")
      ? response({ detail: "Dictionary unavailable" }, 503)
      : undefined,
  );
  await openPopup();
  await click("学校");
  expect(container.textContent).toContain("Dictionary unavailable");
  expect(container.querySelector(".selected-word")?.textContent).toBe("学校");
  expect(button("Retry word lookup")).toBeTruthy();
  await click("Save without meaning");
  expect(container.textContent).toContain("Saved without meaning");
});

it("copies applied source and reports clipboard failure without claiming success", async () => {
  serviceMock();
  const writeText = vi
    .fn()
    .mockResolvedValueOnce(undefined)
    .mockRejectedValueOnce(new Error("denied"));
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  await openPopup();
  await click("Copy sentence");
  expect(writeText).toHaveBeenCalledWith("学校");
  expect(container.textContent).toContain("Sentence copied.");
  await click("Copied");
  expect(container.textContent).toContain("Could not copy the sentence");
  expect(container.textContent).not.toContain("Sentence copied.");
});

it("cancels drafts without changing applied data and clears dependent state only on Apply", async () => {
  serviceMock();
  await openPopup();
  await click("学校");
  await click("Save this word");
  await click("Edit OCR text");
  expect(document.activeElement).toBe(container.querySelector("textarea"));
  await editDraft("猫");
  expect(container.querySelector(".tokenization-text")?.textContent).toBe(
    "学校",
  );
  await act(async () =>
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
  );
  expect(invokeMock).not.toHaveBeenCalledWith(
    "close_translation_popup",
    expect.anything(),
  );
  expect(container.querySelector("textarea")).toBeNull();
  expect(container.textContent).toContain("Saved locally");
  expect(document.activeElement).toBe(button("Edit OCR text"));
  await click("Edit OCR text");
  await editDraft("猫");
  await click("Apply and analyze");
  expect(container.querySelector(".tokenization-text")?.textContent).toBe("猫");
  expect(container.querySelector(".word-definition")).toBeNull();
  expect(container.textContent).not.toContain("Saved locally");
  expect(document.activeElement).toBe(button("Edit OCR text"));
});

it("ignores old word and save responses after rapid token changes", async () => {
  const first = deferred(),
    save = deferred();
  const catToken = {
    ...schoolToken,
    surface: "猫",
    reading: "ネコ",
    dictionaryForm: "猫",
    start: 2,
    end: 3,
  };
  const fetch = serviceMock((path, body) => {
    if (path.endsWith("/tokenize"))
      return response({
        sourceText: "学校猫",
        tokens: [schoolToken, catToken],
      });
    if (path.endsWith("/word"))
      return body.surface === "学校"
        ? first.promise
        : response({
            entries: [
              {
                ...schoolEntry,
                expression: "猫",
                reading: "ねこ",
                senses: [{ glosses: ["cat"] }],
              },
            ],
          });
    if (path.endsWith("/vocabulary")) return save.promise;
  });
  await openPopup("学校猫");
  await click("学校");
  await click("猫");
  await act(async () => first.resolve(response({ entries: [schoolEntry] })));
  expect(container.querySelector(".selected-word")?.textContent).toBe("猫");
  expect(container.textContent).not.toContain("school");
  await click("Save this word");
  const payload = JSON.parse(
    fetch.mock.calls.find(([url]) => url.endsWith("/vocabulary"))![1]!
      .body as string,
  );
  await click("学校");
  await act(async () =>
    save.resolve(
      response({ ...payload, id: 1, createdAt: "2026-10-14T00:00:00Z" }),
    ),
  );
  expect(container.textContent).not.toContain("Word saved locally.");
});

it("loads compounds only on expansion, retries independently and reuses the result", async () => {
  let first = true;
  const fetch = serviceMock((path) => {
    if (path.endsWith("/kanji/examples")) {
      if (first) {
        first = false;
        return response({ detail: "Compound lookup unavailable" }, 503);
      }
      return response({
        examples: [
          { expression: "学生", reading: "ガクセイ", meanings: ["student"] },
        ],
      });
    }
  });
  await openPopup();
  await click("学校");
  await click("学");
  expect(
    fetch.mock.calls.some(([url]) => url.endsWith("/kanji/examples")),
  ).toBe(false);
  await click("Example compounds");
  expect(container.textContent).toContain("Compound lookup unavailable");
  expect(container.textContent).toContain("Meanings: study");
  await click("Retry compounds");
  expect(container.textContent).toContain("がくせい");
  await click("Example compounds");
  await click("Example compounds");
  await click("学");
  expect(
    fetch.mock.calls.filter(([url]) => url.endsWith("/kanji/examples")),
  ).toHaveLength(2);
});

it("ignores old kanji and compound results when switching character", async () => {
  const kanji = deferred(),
    examples = deferred();
  serviceMock((path, body) => {
    if (path.endsWith("/kanji") && body.character === "学")
      return kanji.promise;
    if (path.endsWith("/kanji/examples")) return examples.promise;
  });
  await openPopup();
  await click("学校");
  await click("学");
  await click("Example compounds");
  await click("校");
  await act(async () => {
    kanji.resolve(
      response({
        character: "学",
        onReadings: ["ガク"],
        kunReadings: [],
        meanings: ["OLD KANJI"],
      }),
    );
    examples.resolve(
      response({
        examples: [
          {
            expression: "学生",
            reading: "がくせい",
            meanings: ["OLD COMPOUND"],
          },
        ],
      }),
    );
  });
  expect(container.querySelector(".kanji-character")?.textContent).toBe("校");
  expect(container.textContent).not.toContain("OLD KANJI");
  expect(container.textContent).not.toContain("OLD COMPOUND");
  expect(button("Example compounds").getAttribute("aria-expanded")).toBe(
    "false",
  );
});

it("invalidates pending sentence-save and clipboard feedback on correction and allows save retry", async () => {
  const oldSave = deferred();
  let saveCount = 0;
  serviceMock((path) => {
    if (!path.endsWith("/sentences")) return;
    saveCount++;
    if (saveCount === 1) return oldSave.promise;
    if (saveCount === 2)
      return response({ detail: "Storage unavailable" }, 503);
  });
  let finishCopy!: () => void;
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: vi.fn(
        () =>
          new Promise<void>((resolve) => {
            finishCopy = resolve;
          }),
      ),
    },
  });
  await openPopup();
  await click("Save sentence");
  await click("Copy sentence");
  expect(button("Saving…").disabled).toBe(true);
  await click("Edit OCR text");
  await editDraft("猫");
  await click("Apply and analyze");
  await act(async () => {
    oldSave.resolve(
      response({
        id: 1,
        sourceText: "学校",
        translatedText: null,
        createdAt: "2026-10-14T00:00:00Z",
      }),
    );
    finishCopy();
  });
  expect(container.textContent).not.toContain("Sentence saved locally.");
  expect(container.textContent).not.toContain("Sentence copied.");
  await click("Save sentence");
  expect(container.textContent).toContain("Storage unavailable");
  await click("Save sentence");
  expect(container.textContent).toContain("Sentence saved locally.");
  expect(container.textContent).not.toContain("Storage unavailable");
});
