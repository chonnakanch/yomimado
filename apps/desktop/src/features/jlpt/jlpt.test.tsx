// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { jlptLevel } from "./jlpt";
import { jlptPreferenceKey, setJlptVisible } from "./preference";
import { WordDefinition } from "../translation/WordDefinition";
import { SavedWordsView } from "../library/SavedWordsView";
import { ReadingSettings } from "../settings/ReadingSettings";
import { AboutSettings } from "../settings/AboutSettings";

let container: HTMLDivElement;
let root: Root;
const token = {
  surface: "食べた",
  dictionaryForm: "食べる",
  reading: "タベタ",
  start: 0,
  end: 3,
  partOfSpeech: "動詞",
};
const entry = {
  expression: "食べる",
  reading: "たべる",
  senses: [{ glosses: ["to eat"] }],
  match: "dictionaryForm" as const,
  readingMatch: false,
  common: true,
};

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
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

it("matches exact spellings and normalized readings while keeping homophones distinct", () => {
  expect(jlptLevel("学校", "ガッコウ")).toBe("N5");
  expect(jlptLevel("学校", "ｶﾞｯｺｳ")).toBe("N5");
  expect(jlptLevel("今日", "きょう")).toBe("N5");
  expect(jlptLevel("今日", "こんにち")).toBe("N3");
  expect(jlptLevel("上手", "じょうず")).toBe("N5");
  expect(jlptLevel("上手", "うわて")).toBe("N1");
  expect(jlptLevel("学校", "がくえん")).toBeUndefined();
  expect(jlptLevel("学校", "")).toBeUndefined();
  expect(jlptLevel("生徒会長", "せいとかいちょう")).toBeUndefined();
  expect(jlptLevel("食べた", "たべた")).toBeUndefined();
});

async function mountLearningViews() {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        words: [
          {
            id: 1,
            surface: "食べた",
            dictionaryForm: "食べる",
            reading: "タベル",
            meanings: ["to eat"],
            sourceText: "食べた。",
            createdAt: "2026-10-19T00:00:00Z",
          },
          {
            id: 2,
            surface: "生徒会長",
            dictionaryForm: "生徒会長",
            reading: "せいとかいちょう",
            meanings: [],
            sourceText: "彼は生徒会長です。",
            createdAt: "2026-10-19T00:00:00Z",
          },
        ],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await act(async () =>
    root.render(
      <>
        <ReadingSettings active={false} />
        <WordDefinition
          token={token}
          entries={[entry]}
          loading={false}
          error={null}
          saving={false}
          savedIndex={null}
          saveError={null}
          onSave={vi.fn()}
          onRetry={vi.fn()}
        />
        <SavedWordsView active />
      </>,
    ),
  );
  return fetch;
}

it("uses the same offline badge for a dictionary match and an existing inflected saved record", async () => {
  const fetch = await mountLearningViews();
  const badges = container.querySelectorAll(".jlpt-badge");
  expect(badges).toHaveLength(2);
  for (const badge of badges) {
    expect(badge.textContent).toBe("N5");
    expect(badge.getAttribute("aria-label")).toBe("Estimated JLPT level N5");
    expect(badge.getAttribute("title")).toContain("Stephen Kraus");
  }
  expect(
    container.querySelectorAll(".library-row")[1].querySelector(".jlpt-badge"),
  ).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toContain("/vocabulary");
});

const jlptCheckbox = () =>
  Array.from(
    container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]'),
  ).find((input) =>
    input.parentElement?.textContent?.includes("Show estimated JLPT levels"),
  )!;

it("hides badges immediately, persists the preference and responds to other windows", async () => {
  await mountLearningViews();
  const checkbox = jlptCheckbox();
  expect(checkbox.checked).toBe(true);
  await act(async () => checkbox.click());
  expect(window.localStorage.getItem(jlptPreferenceKey)).toBe("false");
  expect(container.querySelector(".jlpt-badge")).toBeNull();
  await act(async () => {
    window.localStorage.setItem(jlptPreferenceKey, "true");
    window.dispatchEvent(
      new StorageEvent("storage", { key: jlptPreferenceKey }),
    );
  });
  expect(checkbox.checked).toBe(true);
  expect(container.querySelectorAll(".jlpt-badge")).toHaveLength(2);
  await act(async () => setJlptVisible(false));
  await act(async () => root.unmount());
  root = createRoot(container);
  // Reopening reads the stored preference rather than a component default.
  await act(async () => root.render(<ReadingSettings active={false} />));
  expect(jlptCheckbox().checked).toBe(false);
});

it("reports unavailable preference storage without pretending badges were hidden", async () => {
  await mountLearningViews();
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("Storage unavailable");
  });
  await act(async () => jlptCheckbox().click());
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Could not save",
  );
  expect(container.querySelectorAll(".jlpt-badge")).toHaveLength(2);
  expect(jlptCheckbox().checked).toBe(true);
});

it("bundles full license text and credits with the Sources view", async () => {
  await act(async () => root.render(<AboutSettings />));
  expect(container.querySelector(".jlpt-license pre")?.textContent).toContain(
    "Attribution-ShareAlike 4.0 International",
  );
  expect(container.textContent).toContain("Jonathan Waller");
  expect(container.textContent).toContain("Stephen Kraus");
  expect(container.textContent).toContain("community estimates");
});
