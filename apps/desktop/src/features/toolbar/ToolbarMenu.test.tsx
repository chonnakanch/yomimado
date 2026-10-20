// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { emitTo } from "@tauri-apps/api/event";
import { ToolbarMenu } from "./ToolbarMenu";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ emitTo: vi.fn() }));
let container: HTMLDivElement, root: Root;
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.history.replaceState({}, "", "/?mode=toolbar-menu&request=8");
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "get_toolbar_state" ? { sessionId: null } : undefined,
  );
  vi.mocked(emitTo).mockResolvedValue();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.mocked(invoke).mockReset();
  vi.mocked(emitTo).mockReset();
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

it("hides the toolbar only when tray recovery is available", async () => {
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "get_toolbar_state"
      ? { sessionId: null, trayAvailable: true }
      : undefined,
  );
  await mount();
  expect(button("Hide Toolbar").disabled).toBe(false);
  await act(async () => button("Hide Toolbar").click());
  expect(invoke).toHaveBeenCalledWith("hide_toolbar");
  const calls = vi.mocked(invoke).mock.calls.map(([command]) => command);
  expect(calls.indexOf("close_toolbar_menu")).toBeLessThan(
    calls.indexOf("hide_toolbar"),
  );
});

it("omits hiding when the native tray could not be created", async () => {
  await mount();
  expect(button("Hide Toolbar")).toBeUndefined();
  expect(button("Quit YomiMado").disabled).toBe(false);
});

it("blocks hiding during capture", async () => {
  vi.mocked(invoke).mockResolvedValue({ sessionId: 3, trayAvailable: true });
  await mount();
  expect(button("Hide Toolbar").disabled).toBe(true);
  await act(async () => button("Hide Toolbar").click());
  expect(invoke).not.toHaveBeenCalledWith("hide_toolbar");
});

it("reports a native hide failure to the toolbar", async () => {
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_toolbar_state")
      return { sessionId: null, trayAvailable: true };
    if (command === "hide_toolbar") throw new Error("A scan has started");
  });
  await mount();
  await act(async () => button("Hide Toolbar").click());
  expect(emitTo).toHaveBeenCalledWith(
    "toolbar",
    "toolbar-action-error",
    "More actions failed: A scan has started",
  );
});
it("reports a failed destination to the visible toolbar after dismissing the menu", async () => {
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_toolbar_state") return { sessionId: null };
    if (command === "show_secondary_window")
      throw new Error("Settings window could not be opened");
  });
  await mount();
  await act(async () => button("Settings").click());
  expect(invoke).toHaveBeenCalledWith("close_toolbar_menu");
  expect(emitTo).toHaveBeenCalledWith(
    "toolbar",
    "toolbar-action-error",
    "More actions failed: Settings window could not be opened",
  );
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

function menuGeometry(
  intrinsicHeight: () => number,
  viewportHeight = () => 150,
) {
  const computedStyle = window.getComputedStyle;
  vi.spyOn(window, "getComputedStyle").mockImplementation((element) => {
    const style = computedStyle(element);
    style.borderTopWidth = style.borderBottomWidth = "1px";
    return style;
  });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    function (this: HTMLElement) {
      const height = this.classList.contains("toolbar-menu-content")
        ? intrinsicHeight()
        : viewportHeight();
      return {
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 224,
        bottom: height,
        width: 224,
        height,
        toJSON() {},
      };
    },
  );
}

it("waits for the complete tray-dependent item list before revealing the menu", async () => {
  let resolveState!: (value: unknown) => void;
  const snapshot = new Promise((resolve) => {
    resolveState = resolve;
  });
  menuGeometry(() => container.querySelectorAll("button").length * 35 + 16);
  vi.mocked(invoke).mockImplementation(async (command, args) => {
    if (command === "get_toolbar_state") return snapshot;
    if (command === "position_toolbar_menu")
      return (args as { logicalHeight: number }).logicalHeight;
  });
  await mount();
  expect(invoke).not.toHaveBeenCalledWith(
    "position_toolbar_menu",
    expect.anything(),
  );
  await act(async () => resolveState({ sessionId: null, trayAvailable: true }));
  expect(button("Hide Toolbar")).toBeDefined();
  expect(button("Quit YomiMado")).toBeDefined();
  expect(invoke).toHaveBeenCalledWith("position_toolbar_menu", {
    logicalWidth: 224,
    logicalHeight: 228,
    requestId: 8,
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([cmd]) => cmd === "position_toolbar_menu"),
  ).toHaveLength(1);
});

it.each([1, 1.25, 1.5, 2])(
  "keeps full content sizing stable through native height clamps at scale %s",
  async (scale) => {
    let naturalHeight = 221.2;
    let nativeHeight = 150;
    let notify = () => {};
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: () => void) {
          notify = callback;
        }
        observe() {}
        disconnect() {}
      },
    );
    menuGeometry(
      () => naturalHeight,
      () => nativeHeight,
    );
    const positions: number[] = [];
    vi.mocked(invoke).mockImplementation(async (command, args) => {
      if (command === "get_toolbar_state")
        return { sessionId: null, trayAvailable: true };
      if (command === "position_toolbar_menu") {
        const height = (args as { logicalHeight: number }).logicalHeight;
        positions.push(height);
        nativeHeight = Math.floor(Math.min(height, 160.3) * scale) / scale;
        return nativeHeight;
      }
    });
    await mount();
    expect(positions).toEqual([224]);
    for (let i = 0; i < 5; i++) await act(async () => notify());
    expect(positions).toEqual([224]);
    expect(
      (container.querySelector("[role=menu]") as HTMLElement).style.maxHeight,
    ).toBe(`${nativeHeight}px`);

    // Font metrics/wrapping can change after the first constrained frame.
    naturalHeight = 275.3;
    await act(async () => notify());
    for (let i = 0; i < 5; i++) await act(async () => notify());
    expect(positions).toEqual([224, 278]);
    expect(button("Quit YomiMado").disabled).toBe(false);
  },
);

it("caps oversized intrinsic error content at the native request limit", async () => {
  menuGeometry(() => 900);
  await mount();
  expect(invoke).toHaveBeenCalledWith("position_toolbar_menu", {
    logicalWidth: 224,
    logicalHeight: 600,
    requestId: 8,
  });
});

it("still reveals Quit and an error if the toolbar snapshot fails", async () => {
  menuGeometry(() => 250);
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_toolbar_state")
      throw new Error("Toolbar state unavailable");
  });
  await mount();
  expect(container.querySelector("[role=alert]")?.textContent).toContain(
    "Toolbar state unavailable",
  );
  expect(button("Quit YomiMado").disabled).toBe(false);
  expect(invoke).toHaveBeenCalledWith("position_toolbar_menu", {
    logicalWidth: 224,
    logicalHeight: 252,
    requestId: 8,
  });
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
