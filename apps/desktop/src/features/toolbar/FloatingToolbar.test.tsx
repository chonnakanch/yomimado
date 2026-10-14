// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { listen, type Event } from "@tauri-apps/api/event";
import { FloatingToolbar, type ToolbarState } from "./FloatingToolbar";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));

const initial: ToolbarState = {
  revision: 1,
  sessionId: null,
  phase: "idle",
  message: "Ready to scan Japanese text.",
  canRescan: false,
  hasOverlay: false,
  overlayVisible: false,
  displayName: "Left display",
  availableWidth: 520,
  detectorModel: { required: false, installed: false },
};
let container: HTMLDivElement;
let root: Root;
let snapshot: ToolbarState;
let statusListener: (event: Event<ToolbarState>) => void;
const stopListening = vi.fn();

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
  snapshot = { ...initial };
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "get_toolbar_state" ? snapshot : undefined,
  );
  vi.mocked(listen).mockImplementation(async (_event, callback) => {
    statusListener = callback as (event: Event<ToolbarState>) => void;
    return stopListening;
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

const button = (label: string) =>
  Array.from(container.querySelectorAll("button")).find(
    (b) => b.getAttribute("aria-label") === label || b.textContent === label,
  )!;
const mount = () => act(async () => root.render(<FloatingToolbar />));
const update = (changes: Partial<ToolbarState>) =>
  act(async () =>
    statusListener({
      event: "toolbar-state-changed",
      id: 1,
      payload: { ...snapshot, ...changes },
    }),
  );

it("offers two explicit scan modes and disables Rescan until a successful capture", async () => {
  await mount();
  expect(button("Rescan").disabled).toBe(true);
  expect(button("Show OCR overlays").disabled).toBe(true);
  await act(async () => button("Selected Area").click());
  expect(invoke).toHaveBeenCalledWith("start_toolbar_scan", {
    mode: "selectedArea",
  });
  await act(async () => button("Whole Screen").click());
  expect(invoke).toHaveBeenCalledWith("start_toolbar_scan", {
    mode: "wholeScreen",
  });
  expect(container.textContent).not.toContain("Scan manga page");
});

it("blocks overlapping scans, retains the last Rescan and cancels the exact session", async () => {
  await mount();
  await update({
    revision: 3,
    canRescan: true,
    sessionId: 2,
    phase: "recognizing",
    message: "Recognizing Japanese text locally…",
  });
  expect(button("Selected Area").disabled).toBe(true);
  expect(button("Rescan").disabled).toBe(true);
  expect(container.textContent).toContain("Recognizing");
  await act(async () => button("Cancel scan").click());
  expect(invoke).toHaveBeenCalledWith("cancel_capture_selector", {
    sessionId: 2,
  });
  await update({ revision: 4, canRescan: true });
  await act(async () => button("Rescan").click());
  expect(invoke).toHaveBeenCalledWith("rescan", undefined);
});

it("ignores older snapshots and toggles native visibility without requesting OCR", async () => {
  await mount();
  await update({ revision: 8, hasOverlay: true, overlayVisible: true });
  await update({ revision: 2, hasOverlay: false, overlayVisible: false });
  await act(async () => button("Hide OCR overlays").click());
  expect(invoke).toHaveBeenCalledWith("set_overlay_visibility", {
    visible: false,
  });
  expect(invoke).not.toHaveBeenCalledWith(
    "start_toolbar_scan",
    expect.anything(),
  );
});

it("shows missing-model setup through Settings and preserves service errors", async () => {
  snapshot = {
    ...initial,
    detectorModel: { required: true, installed: false },
  };
  await mount();
  expect(button("Whole Screen").disabled).toBe(true);
  await act(async () => button("Scan & OCR").click());
  expect(invoke).toHaveBeenCalledWith("show_secondary_window", {
    view: "settings",
  });
  await update({
    revision: 4,
    detectorModel: { required: true, installed: true },
  });
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "start_toolbar_scan")
      throw new Error("Screen Recording access is required");
    return snapshot;
  });
  await act(async () => button("Whole Screen").click());
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Screen Recording access is required",
  );
});

it("shrinks native bounds when collapsed and restores the saved preference", async () => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
    function (this: HTMLElement) {
      const collapsed = this.classList.contains("collapsed");
      return {
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: collapsed ? 112 : 520,
        bottom: collapsed ? 48 : 56,
        width: collapsed ? 112 : 520,
        height: collapsed ? 48 : 56,
        toJSON() {},
      };
    },
  );
  await mount();
  await act(async () => button("Collapse toolbar").click());
  expect(invoke).toHaveBeenCalledWith("resize_toolbar", {
    logicalWidth: 112,
    logicalHeight: 48,
  });
  expect(window.localStorage.getItem("yomimado.toolbar.collapsed.v1")).toBe(
    "true",
  );
  expect(button("Expand toolbar")).toBeDefined();
  expect(container.textContent).not.toContain("Selected Area");
  await act(async () => root.unmount());
  root = createRoot(container);
  await mount();
  expect(button("Expand toolbar")).toBeDefined();
});

it("supports keyboard menu navigation, Escape focus return, movement and listener cleanup", async () => {
  await mount();
  await act(async () =>
    button("Move toolbar").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenCalledWith("move_toolbar", { dx: -8, dy: 0 });
  await act(async () => button("More actions").click());
  expect(document.activeElement).toBe(button("Saved words"));
  await act(async () =>
    button("Saved words").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("Saved sentences"));
  await act(async () =>
    button("Saved sentences").dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("More actions"));
  await act(async () => root.unmount());
  expect(stopListening).toHaveBeenCalled();
  root = createRoot(container);
});

it("offers region focus only for a visible result and invokes native keyboard entry", async () => {
  await mount();
  await act(async () => button("More actions").click());
  expect(button("Focus regions").disabled).toBe(true);
  await update({ revision: 2, hasOverlay: true, overlayVisible: true });
  expect(button("Focus regions").disabled).toBe(false);
  await act(async () => button("Focus regions").click());
  expect(invoke).toHaveBeenCalledWith("focus_ocr_regions", undefined);
});
