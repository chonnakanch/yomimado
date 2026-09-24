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

it("preserves OCR text and translates only after a click", async () => {
  const state = encodeURIComponent(
    JSON.stringify({ text: "学校", demo: false }),
  );
  window.history.replaceState({}, "", `/?mode=translation&state=${state}`);
  const fetch = vi.fn().mockResolvedValue(
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
  vi.stubGlobal("fetch", fetch);

  await act(async () => root.render(<TranslationPopup />));
  expect(
    (container.querySelector("textarea") as HTMLTextAreaElement).value,
  ).toBe("学校");
  expect(fetch).not.toHaveBeenCalled();

  await act(async () => {
    container.querySelector<HTMLButtonElement>(".translate-button")!.click();
  });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("School");
  expect(container.textContent).toContain("cached");
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
