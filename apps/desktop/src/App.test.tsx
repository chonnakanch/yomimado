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
      .find((button) => button.textContent === "Saved words")!
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
  expect(fetch.mock.calls[1][1]).toEqual({ method: "DELETE" });
  expect(container.textContent).toContain("No saved words yet");
});

it("shows saved sentences and removes one only after confirmation", async () => {
  const sentence = {
    id: 3,
    sourceText: "今日はいい日だ。",
    translatedText: "It's a good day.",
    createdAt: "2026-09-28T12:00:00+00:00",
  };
  const fetch = vi.fn((_url: string, options?: RequestInit) => {
    if (options?.method === "DELETE")
      return Promise.resolve(new Response(null, { status: 204 }));
    return Promise.resolve(
      new Response(JSON.stringify({ sentences: [sentence] })),
    );
  });
  vi.stubGlobal("fetch", fetch);
  const confirm = vi.fn().mockReturnValue(false);
  vi.stubGlobal("confirm", confirm);

  await act(async () => root.render(<App />));
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => {
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Saved sentences")!
      .click();
  });
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
  expect(fetch).toHaveBeenCalledTimes(1);

  confirm.mockReturnValue(true);
  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(
        '[aria-label="Remove saved sentence 3"]',
      )!
      .click();
  });
  expect(fetch.mock.calls[1][1]).toEqual({ method: "DELETE" });
  expect(container.textContent).toContain("No saved sentences yet");
});
