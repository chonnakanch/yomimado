// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { App } from "../../App";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

const contents = JSON.stringify({
  format: "yomimado-saved",
  version: 1,
  createdAt: "2026-10-23T00:00:00Z",
  words: [],
  sentences: [],
});
const file = { name: "my-saved-backup.json", contents };
const summary = {
  wordsAdded: 1,
  wordsSkipped: 2,
  sentencesAdded: 1,
  sentencesSkipped: 3,
};
const word = {
  id: 7,
  surface: "学校",
  reading: "ガッコウ",
  dictionaryForm: "学校",
  meanings: ["school"],
  sourceText: "学校に行く。",
  createdAt: "2026-09-01T00:00:00Z",
};
const sentence = {
  id: 2,
  sourceText: "学校に行く。",
  translatedText: "Going to school.",
  createdAt: word.createdAt,
};
let container: HTMLDivElement;
let root: Root;
let restored: boolean;
let fetchMock: ReturnType<
  typeof vi.fn<(url: string, options?: RequestInit) => Promise<Response>>
>;
let restoreFailure: boolean;
let previewSummary: typeof summary;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
  window.history.replaceState({}, "", "/?view=saved");
  restored = false;
  restoreFailure = false;
  previewSummary = summary;
  vi.mocked(invoke).mockReset();
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "choose_learning_backup" ? file : true,
  );
  fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    const path = new URL(url).pathname;
    if (path === "/api/v1/backup") return new Response(contents);
    if (path.endsWith("/preview")) return Response.json(previewSummary);
    if (path.endsWith("/restore")) {
      if (restoreFailure)
        return Response.json(
          { detail: "Storage unavailable; no entries were added" },
          { status: 503 },
        );
      restored = true;
      return Response.json(summary);
    }
    if (path === "/api/v1/vocabulary")
      return Response.json({ words: restored ? [word] : [] });
    if (path === "/api/v1/sentences")
      return Response.json({ sentences: restored ? [sentence] : [] });
    throw new Error(`Unexpected request: ${path} ${options?.method ?? "GET"}`);
  });
  vi.stubGlobal("fetch", fetchMock);
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
function button(label: string) {
  const result = Array.from(
    container.querySelectorAll<HTMLButtonElement>("button"),
  ).find((b) => b.textContent?.trim() === label);
  if (!result) throw new Error(`Button missing: ${label}`);
  return result;
}
async function click(label: string) {
  await act(async () => button(label).click());
}
async function open() {
  await act(async () => root.render(<App />));
  await act(async () =>
    container.querySelector<HTMLElement>(".library-backup summary")!.click(),
  );
}
const requests = (suffix: string) =>
  fetchMock.mock.calls.filter(([url]) => (url as string).endsWith(suffix));

it("exports the whole library only on request and confirms native save success", async () => {
  await open();
  expect(requests("/backup")).toHaveLength(0);
  expect(invoke).not.toHaveBeenCalled();
  await click("Export backup");
  expect(invoke).toHaveBeenCalledExactlyOnceWith("save_learning_backup", {
    contents,
  });
  expect(requests("/backup")[0][1]).toEqual({
    headers: { "x-yomimado-client": "desktop" },
  });
  expect(container.textContent).toContain("Backup saved.");
  expect(requests("/restore")).toHaveLength(0);
});

it.each(["Export backup", "Restore backup"])(
  "treats native cancellation of %s as a no-op",
  async (action) => {
    vi.mocked(invoke).mockResolvedValue(
      action === "Restore backup" ? null : false,
    );
    await open();
    await click(action);
    expect(container.textContent).toContain(
      action === "Restore backup" ? "Restore canceled." : "Export canceled.",
    );
    expect(
      container.querySelector('[aria-label="Restore preview"]'),
    ).toBeNull();
    expect(requests("/preview")).toHaveLength(0);
    expect(requests("/restore")).toHaveLength(0);
    expect(container.textContent).not.toContain("Backup saved.");
  },
);

it("previews duplicate counts before any writes, and cancel restores keyboard focus", async () => {
  await open();
  await click("Restore backup");
  expect(container.textContent).toContain("1 new word · 2 duplicates skipped");
  expect(container.textContent).toContain(
    "1 new sentence · 3 duplicates skipped",
  );
  expect(container.textContent).toContain(file.name);
  expect(document.activeElement).toBe(button("Restore missing entries"));
  expect(requests("/restore")).toHaveLength(0);
  await click("Cancel restore");
  expect(document.activeElement).toBe(button("Restore backup"));
  expect(requests("/restore")).toHaveLength(0);
});

it("restores only on confirmation, refreshes both collections and preserves the search", async () => {
  await open();
  const input = container.querySelector<HTMLInputElement>(
    'input[type="search"]',
  )!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!.call(input, "がっこう");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await click("Restore backup");
  await act(async () => {
    button("Restore missing entries").click();
    button("Restore missing entries").click();
  });
  expect(requests("/restore")).toHaveLength(1);
  expect(requests("/restore")[0][1]).toMatchObject({
    method: "POST",
    body: contents,
    headers: {
      "x-yomimado-client": "desktop",
      "content-type": "application/json",
    },
  });
  expect(container.textContent).toContain(
    "Restored 1 word and 1 sentence; skipped 5 duplicates.",
  );
  expect(container.querySelector(".library-word strong")?.textContent).toBe(
    "学校",
  );
  expect(input.value).toBe("がっこう");
  expect(requests("/api/v1/vocabulary")).toHaveLength(2);
  expect(document.activeElement).toBe(button("Restore backup"));
  await click("Sentences");
  expect(
    container.querySelector("#saved-panel-sentences")?.textContent,
  ).toContain("Going to school.");
  expect(
    fetchMock.mock.calls.some(([url]) =>
      /translate|word$|tokenize/.test(url as string),
    ),
  ).toBe(false);
});

it("refreshes restored entries after an already pending removal finishes", async () => {
  let finishDelete!: (response: Response) => void;
  let deleted = false;
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method === "DELETE")
      return new Promise<Response>((resolve) => {
        finishDelete = resolve;
      });
    if (url.endsWith("/api/v1/vocabulary"))
      return Promise.resolve(
        Response.json({
          words: [deleted ? { ...word, id: 8, surface: "本" } : word],
        }),
      );
    return original(url, options);
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  await open();
  await click("Remove");
  await click("Restore backup");
  await click("Restore missing entries");
  expect(requests("/api/v1/vocabulary")).toHaveLength(1);
  await act(async () => {
    deleted = true;
    finishDelete(new Response(null, { status: 204 }));
  });
  expect(requests("/api/v1/vocabulary")).toHaveLength(2);
  expect(container.querySelector(".library-word strong")?.textContent).toBe(
    "本",
  );
});

it("retains the preview after storage failure and allows retry without rereading the file", async () => {
  restoreFailure = true;
  await open();
  await click("Restore backup");
  await click("Restore missing entries");
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Storage unavailable",
  );
  expect(
    container.querySelector('[aria-label="Restore preview"]'),
  ).not.toBeNull();
  expect(restored).toBe(false);
  restoreFailure = false;
  await click("Restore missing entries");
  expect(requests("/restore")).toHaveLength(2);
  expect(invoke).toHaveBeenCalledTimes(1);
  expect(container.querySelector('[role="alert"]')).toBeNull();
});

it("keeps an all-duplicate preview readable without offering another restore", async () => {
  previewSummary = {
    wordsAdded: 0,
    wordsSkipped: 2,
    sentencesAdded: 0,
    sentencesSkipped: 3,
  };
  await open();
  await click("Restore backup");
  expect(button("Restore missing entries").disabled).toBe(true);
  expect(container.textContent).toContain("Nothing new to restore.");
  expect(document.activeElement).toBe(
    container.querySelector('[aria-label="Restore preview"]'),
  );
  await click("Cancel restore");
  expect(requests("/restore")).toHaveLength(0);
});

it("shows file and export failures without claiming success", async () => {
  vi.mocked(invoke).mockRejectedValue(new Error("Could not read backup"));
  await open();
  await click("Restore backup");
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Could not read backup",
  );
  expect(requests("/preview")).toHaveLength(0);
  await click("Export backup");
  expect(container.textContent).not.toContain("Backup saved.");
  expect(container.querySelector('[role="alert"]')).not.toBeNull();
});

it.each([
  null,
  {},
  { ...summary, wordsAdded: -1 },
  { ...summary, sentencesSkipped: "2" },
])(
  "rejects an invalid preview response without exposing restore",
  async (invalid) => {
    await open();
    fetchMock.mockImplementation(async () => Response.json(invalid));
    await click("Restore backup");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      "invalid data",
    );
    expect(
      container.querySelector('[aria-label="Restore preview"]'),
    ).toBeNull();
    expect(requests("/restore")).toHaveLength(0);
  },
);
