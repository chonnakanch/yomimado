// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { TranslationModels } from "./TranslationModels";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
  isTauri: () => true,
}));
let container: HTMLDivElement;
let root: Root;
let settings: {
  provider: string;
  importedModel: string | null;
  ollamaModel: string;
  backend: string;
};
let download = {
  state: "idle",
  model: "",
  message: "",
  completed: 0,
  total: 0,
};
let models = [{ name: "my-model:latest", digest: "a".repeat(64) }];
const response = (body: unknown, ok = true) => ({
  ok,
  status: ok ? 200 : 422,
  json: async () => body,
});
const fetch = vi.fn(async (url: string, options?: RequestInit) => {
  const body = options?.body ? JSON.parse(String(options.body)) : {};
  if (url.endsWith("/translation-model"))
    return response({
      state: "notInstalled",
      receivedBytes: 0,
      downloadBytes: 1000,
      error: null,
    });
  if (url.endsWith("/ollama/pull")) {
    download = {
      state: "downloading",
      model: body.model.includes(":") ? body.model : body.model + ":latest",
      message: "Pulling weights",
      completed: 50,
      total: 100,
    };
    return response(download);
  }
  if (url.endsWith("/ollama"))
    return response({ models, error: null, download });
  if (url.endsWith("/import"))
    settings = {
      ...settings,
      provider: "imported",
      importedModel: "my-translator",
    };
  else if (options?.method === "POST")
    settings = {
      ...settings,
      provider: body.provider,
      ollamaModel: body.model,
    };
  return response(settings);
});
const button = (label: string) =>
  Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find(
    (item) => item.textContent === label,
  )!;
const click = (label: string) => act(async () => button(label).click());
const source = (value: string) =>
  act(async () => {
    const select = container.querySelector("select")!;
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
const input = (value: string) =>
  act(async () => {
    const field = container.querySelector("input")!;
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  settings = {
    provider: "builtin",
    importedModel: null,
    ollamaModel: "",
    backend: "torch",
  };
  download = { state: "idle", model: "", message: "", completed: 0, total: 0 };
  models = [{ name: "my-model:latest", digest: "a".repeat(64) }];
  fetch.mockClear();
  vi.stubGlobal("fetch", fetch);
  vi.mocked(invoke).mockReset();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});
const mount = () => act(async () => root.render(<TranslationModels active />));

it("loads the saved choice without downloading or activating a browsed source", async () => {
  await mount();
  await source("ollama");
  expect(container.textContent).toContain("Using: Built-in Marian model");
  expect(container.textContent).toContain("my-model:latest");
  expect(
    fetch.mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
});

it("imports a chosen folder and immediately shows the selected model", async () => {
  vi.mocked(invoke).mockResolvedValue("/models/my-translator");
  await mount();
  await source("imported");
  await click("Browse folders…");
  expect(container.querySelector("input")?.value).toBe("/models/my-translator");
  await click("Import and use model");
  expect(container.textContent).toContain("Using: my-translator");
  expect(
    fetch.mock.calls.some(
      ([url, options]) =>
        url.endsWith("/import") &&
        JSON.parse(String(options?.body)).folder === "/models/my-translator",
    ),
  ).toBe(true);
});

it("does not import or change selection when the folder picker is cancelled", async () => {
  vi.mocked(invoke).mockResolvedValue(null);
  await mount();
  await source("imported");
  await click("Browse folders…");
  expect(button("Import and use model").disabled).toBe(true);
  expect(
    fetch.mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
});

it("keeps the current provider visible after an incompatible import", async () => {
  await mount();
  await source("imported");
  await input("/models/incompatible");
  fetch.mockResolvedValueOnce(
    response(
      { detail: "Import a Japanese-to-English Marian model folder" },
      false,
    ),
  );
  await click("Import and use model");
  expect(container.textContent).toContain("Using: Built-in Marian model");
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Marian model folder",
  );
});

it("selects an installed Ollama model only on Use this model", async () => {
  await mount();
  await source("ollama");
  await input("my-model:latest");
  await click("Use this model");
  expect(container.textContent).toContain("Using: Ollama · my-model:latest");
  expect(
    fetch.mock.calls.filter(([, options]) => options?.method === "POST"),
  ).toHaveLength(1);
});

it("keeps the Ollama panel and model name while an explicit pull runs", async () => {
  await mount();
  await source("ollama");
  await input("another-model");
  await click("Download in Ollama");
  expect(container.querySelector("select")?.value).toBe("ollama");
  expect(container.querySelector("input")?.value).toBe("another-model:latest");
  expect(container.querySelector("progress")?.value).toBe(50);
  expect(button("Downloading…").disabled).toBe(true);
  expect(container.textContent).toContain("Using: Built-in Marian model");
});

it("restores an Ollama selection without contacting chat or pulling a model", async () => {
  settings = {
    ...settings,
    provider: "ollama",
    ollamaModel: "my-model:latest",
  };
  await mount();
  expect(container.querySelector("select")?.value).toBe("ollama");
  expect(container.textContent).toContain("Using: Ollama · my-model:latest");
  expect(
    fetch.mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
});
