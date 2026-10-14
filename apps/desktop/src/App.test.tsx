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

it("keeps reading-order controls disabled until enabled in settings", async () => {
  await act(async () => root.render(<App />));
  const setting = container.querySelector<HTMLInputElement>(
    'input[type="checkbox"]',
  )!;
  expect(setting.checked).toBe(false);

  await act(async () => setting.click());
  expect(setting.checked).toBe(true);
  expect(window.localStorage.getItem("yomimado.reading-order.enabled.v1")).toBe(
    "true",
  );

  await act(async () => root.unmount());
  root = createRoot(container);
  await act(async () => root.render(<App />));
  expect(
    container.querySelector<HTMLInputElement>('input[type="checkbox"]')
      ?.checked,
  ).toBe(true);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.mocked(invoke).mockReset();
});

it("starts a one-shot automatic scan from the main window", async () => {
  vi.mocked(invoke).mockResolvedValue(undefined);
  await act(async () => root.render(<App />));
  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Scan manga page")!
      .click();
  });
  expect(invoke).toHaveBeenCalledWith("show_auto_scanner");
  expect(container.textContent).toContain("Finding the manga page");
});

it("opens the scan-area adjustment selector", async () => {
  vi.mocked(invoke).mockResolvedValue(undefined);
  await act(async () => root.render(<App />));
  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Set/adjust scan area")!
      .click();
  });
  expect(invoke).toHaveBeenCalledWith("show_scan_area_selector");
});

it("shows dictionary attribution from the sources control", async () => {
  await act(async () => root.render(<App />));
  const button = Array.from(container.querySelectorAll("button")).find(
    (item) => item.textContent === "Sources and licenses",
  )!;
  expect(button.getAttribute("aria-expanded")).toBe("false");
  await act(async () => button.click());
  expect(button.getAttribute("aria-expanded")).toBe("true");
  expect(container.textContent).toContain("JMdict and KANJIDIC2");
  expect(container.textContent).toContain("Electronic Dictionary Research");
  expect(
    container.querySelector<HTMLAnchorElement>(
      'a[href="https://www.edrdg.org/edrdg/licence.html"]',
    ),
  ).not.toBeNull();
});

it("requires manual detector installation before packaged scans", async () => {
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "detector_model_status") {
      return { required: true, installed: false };
    }
    if (command === "install_detector_model") {
      return { required: true, installed: true };
    }
    return undefined;
  });
  await act(async () => root.render(<App />));
  expect(container.textContent).toContain("original release page");
  expect(
    Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Scan manga page",
    )?.disabled,
  ).toBe(true);

  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Select detector model file")!
      .click();
  });
  expect(invoke).toHaveBeenCalledWith("install_detector_model");
  expect(container.textContent).toContain("Manga scanning is ready");
  expect(container.textContent).toContain("Installed on this computer");
  expect(
    Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Scan manga page",
    )?.disabled,
  ).toBe(false);
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

  await act(async () => root.render(<App />));
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Saved")!
      .click();
  });
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

  await act(async () => root.render(<App />));
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Saved")!
      .click();
  });
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

it("preserves independent collection errors and refreshes on reopening", async () => {
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
  await click("Saved");
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
  await click("Hide saved");
  expect(container.querySelector(".saved-library")).toBeNull();
  await click("Saved");
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
