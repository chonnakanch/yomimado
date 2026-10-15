// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { ToolbarMenu } from "./ToolbarMenu";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
let container: HTMLDivElement, root: Root;
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.history.replaceState({}, "", "/?mode=toolbar-menu&request=8");
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "get_toolbar_state" ? { sessionId: null } : undefined,
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.mocked(invoke).mockReset();
});
const button = (label: string) =>
  [...container.querySelectorAll<HTMLButtonElement>("button")].find(
    (item) => item.textContent === label,
  )!;
const mount = () => act(async () => root.render(<ToolbarMenu />));
it("supports arrow navigation, Escape and native focus return", async () => {
  await mount();
  expect(document.activeElement).toBe(button("Saved"));
  await act(async () =>
    button("Saved").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("Settings"));
  expect(container.querySelector("[role=menu]")?.classList).toContain(
    "keyboard-navigation",
  );
  await act(async () =>
    button("Settings").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenCalledWith("close_toolbar_menu", {
    restoreFocus: true,
  });
});
it("keeps mouse opening quiet and switches the focus indicator with input", async () => {
  await mount();
  const menu = container.querySelector("[role=menu]")!;
  expect(document.activeElement).toBe(button("Saved"));
  expect(menu.classList).not.toContain("keyboard-navigation");
  await act(async () =>
    button("Saved").dispatchEvent(
      new KeyboardEvent("keydown", { key: "End", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("Quit YomiMado"));
  expect(menu.classList).toContain("keyboard-navigation");
  await act(async () =>
    button("Settings").dispatchEvent(
      new Event("pointermove", { bubbles: true }),
    ),
  );
  expect(menu.classList).not.toContain("keyboard-navigation");
  await act(async () =>
    button("Quit YomiMado").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Home", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("Saved"));
  expect(menu.classList).toContain("keyboard-navigation");
});
it("opens one grouped Saved destination after dismissing the menu", async () => {
  await mount();
  await act(async () => button("Saved").click());
  expect(
    [...container.querySelectorAll("button")].map((b) => b.textContent),
  ).toEqual([
    "Read with keyboard",
    "Saved",
    "Settings",
    "Sources & licenses",
    "Quit YomiMado",
  ]);
  expect(invoke).toHaveBeenCalledWith("close_toolbar_menu");
  expect(invoke).toHaveBeenCalledWith("show_secondary_window", {
    view: "saved",
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.findIndex(([command]) => command === "close_toolbar_menu"),
  ).toBeLessThan(
    vi
      .mocked(invoke)
      .mock.calls.findIndex(([command]) => command === "show_secondary_window"),
  );
});
it("blocks secondary views during scans but keeps Quit available", async () => {
  vi.mocked(invoke).mockResolvedValue({ sessionId: 3 });
  await mount();
  expect(button("Saved").disabled).toBe(true);
  expect(button("Settings").disabled).toBe(true);
  expect(button("Quit YomiMado").disabled).toBe(false);
  await act(async () => button("Quit YomiMado").click());
  expect(invoke).toHaveBeenCalledWith("quit_app", undefined);
});
it("positions only its own native popover using the current request generation", async () => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    function () {
      return {
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 224,
        bottom: 154,
        width: 224,
        height: 154,
        toJSON() {},
      };
    },
  );
  await mount();
  expect(invoke).toHaveBeenCalledWith("position_toolbar_menu", {
    logicalWidth: 224,
    logicalHeight: 154,
    requestId: 8,
  });
  expect(invoke).not.toHaveBeenCalledWith("resize_toolbar", expect.anything());
});

it("explicitly enters region navigation only for a visible idle OCR result", async () => {
  vi.mocked(invoke).mockResolvedValue({
    sessionId: null,
    hasOverlay: true,
    overlayVisible: true,
  });
  await mount();
  expect(document.activeElement).toBe(button("Read with keyboard"));
  await act(async () => button("Read with keyboard").click());
  expect(invoke).toHaveBeenCalledWith("focus_ocr_regions");
  expect(
    vi
      .mocked(invoke)
      .mock.calls.findIndex(([name]) => name === "close_toolbar_menu"),
  ).toBeLessThan(
    vi
      .mocked(invoke)
      .mock.calls.findIndex(([name]) => name === "focus_ocr_regions"),
  );
});
it.each([
  { sessionId: null, hasOverlay: false, overlayVisible: false },
  { sessionId: null, hasOverlay: true, overlayVisible: false },
  { sessionId: 1, hasOverlay: true, overlayVisible: true },
])(
  "does not enable keyboard reading without visible, completed regions: %j",
  async (state) => {
    vi.mocked(invoke).mockResolvedValue(state);
    await mount();
    expect(button("Read with keyboard").disabled).toBe(true);
    await act(async () => button("Read with keyboard").click());
    expect(invoke).not.toHaveBeenCalledWith("focus_ocr_regions");
  },
);
