// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TranslationDownload } from "./TranslationDownload";

let container: HTMLDivElement;
let root: Root;
const status = (state: string, error: string | null = null) => ({
  state,
  error,
  receivedBytes: state === "downloading" ? 100 : 0,
  downloadBytes: 1000,
});
const response = (body: unknown) => ({ ok: true, json: async () => body });

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

it("checks status without downloading and installs only on a user click", async () => {
  let installed = false;
  const fetch = vi.fn(async (_url: string, options?: RequestInit) => {
    if (options?.method === "POST") installed = true;
    return response(status(installed ? "ready" : "notInstalled"));
  });
  vi.stubGlobal("fetch", fetch);
  await act(async () => root.render(<TranslationDownload active={false} />));
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => root.render(<TranslationDownload active />));
  expect(
    fetch.mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
  expect(container.textContent).toContain("Not installed");
  await act(async () => container.querySelector("button")!.click());
  expect(
    fetch.mock.calls.filter(([, options]) => options?.method === "POST"),
  ).toHaveLength(1);
  expect(container.textContent).toContain("Ready for offline translation");
  expect(container.querySelector("button")).toBeNull();
});

it("shows download progress and prevents duplicate install clicks", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => response(status("downloading"))),
  );
  await act(async () => root.render(<TranslationDownload active />));
  expect(container.querySelector("progress")?.value).toBe(100);
  expect(container.querySelector("button")?.disabled).toBe(true);
});

it("offers retry after a failed download", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => response(status("error", "Connection interrupted"))),
  );
  await act(async () => root.render(<TranslationDownload active />));
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Connection interrupted",
  );
  expect(container.querySelector("button")?.textContent).toBe("Retry download");
});
