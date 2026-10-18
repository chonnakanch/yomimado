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
  expect(container.textContent).toContain(
    "Scan manga text, click a detected region, then choose Translate locally.",
  );
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

it("explains a service connection failure and recovers without downloading", async () => {
  const fetch = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("Load failed"))
    .mockResolvedValue(response(status("ready")));
  vi.stubGlobal("fetch", fetch);
  await act(async () => root.render(<TranslationDownload active />));
  expect(container.querySelector('[role="status"]')?.textContent).toBe(
    "Translation setup could not be checked.",
  );
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Quit and reopen YomiMado, then try again.",
  );
  expect(container.textContent).not.toContain("Checking translation setup");
  expect(container.textContent).not.toContain("Load failed");
  await act(async () => container.querySelector("button")!.click());
  expect(container.textContent).toContain("Ready for offline translation");
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(
    fetch.mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
});

it("keeps a failed install request visible until the user retries", async () => {
  const fetch = vi.fn(async (_url: string, options?: RequestInit) => {
    if (options?.method === "POST") throw new TypeError("Load failed");
    return response(status("notInstalled"));
  });
  vi.stubGlobal("fetch", fetch);
  await act(async () => root.render(<TranslationDownload active />));
  await act(async () => container.querySelector("button")!.click());
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "local service",
  );
  expect(container.querySelector("button")?.textContent).toBe("Try again");
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("allows reconnecting when a download status poll loses the service", async () => {
  vi.useFakeTimers();
  try {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response(status("downloading")))
      .mockRejectedValueOnce(new TypeError("Load failed"))
      .mockResolvedValue(response(status("ready")));
    vi.stubGlobal("fetch", fetch);
    await act(async () => root.render(<TranslationDownload active />));
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(container.querySelector("progress")).toBeNull();
    expect(container.querySelector("button")?.disabled).toBe(false);
    expect(container.querySelector("button")?.textContent).toBe("Try again");
    await act(async () => container.querySelector("button")!.click());
    expect(container.textContent).toContain("Ready for offline translation");
  } finally {
    vi.useRealTimers();
  }
});
