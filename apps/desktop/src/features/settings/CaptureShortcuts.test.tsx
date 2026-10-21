// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { listen, type Event } from "@tauri-apps/api/event";
import { CaptureShortcuts } from "./CaptureShortcuts";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));
const defaults = {
  selectedArea: "control+shift+KeyO",
  wholeScreen: "control+shift+KeyS",
};
const initial = {
  bindings: defaults,
  defaults,
  available: [true, true],
  warnings: [],
};
let container: HTMLDivElement;
let root: Root;
let recorded: (event: Event<string>) => void;
let cleanup = vi.fn<() => void>();

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.spyOn(document, "hasFocus").mockReturnValue(true);
  cleanup = vi.fn<() => void>();
  vi.mocked(listen).mockImplementation(async (_name, handler) => {
    recorded = handler as typeof recorded;
    return cleanup;
  });
  vi.mocked(invoke).mockImplementation(async (command, args) => {
    if (command === "capture_shortcuts") return initial;
    if (command === "set_capture_shortcuts")
      return {
        ...initial,
        bindings: (args as { bindings: typeof defaults }).bindings,
      };
    return undefined;
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.mocked(invoke).mockReset();
  vi.mocked(listen).mockReset();
});
const mount = (active = true) =>
  act(async () => root.render(<CaptureShortcuts active={active} />));
const change = (label = "Selected Area") =>
  container.querySelector<HTMLButtonElement>(
    `[aria-label="Change ${label} shortcut"]`,
  )!;
const begin = (label = "Selected Area") =>
  act(async () => change(label).click());
const key = (type: string, options: KeyboardEventInit) =>
  act(async () => {
    window.dispatchEvent(
      new KeyboardEvent(type, { bubbles: true, cancelable: true, ...options }),
    );
  });
const saves = () =>
  vi
    .mocked(invoke)
    .mock.calls.filter(([name]) => name === "set_capture_shortcuts");

it("records physical keys on release, applies immediately and restores focus", async () => {
  await mount();
  expect(container.textContent).toContain("Ctrl + Shift + O");
  await begin();
  expect(invoke).toHaveBeenCalledWith("record_capture_shortcut", {
    recording: true,
  });
  await key("keydown", {
    key: "K",
    code: "KeyK",
    ctrlKey: true,
    shiftKey: true,
  });
  expect(saves()).toHaveLength(0);
  await key("keyup", { key: "K", code: "KeyK" });
  expect(saves()).toEqual([
    [
      "set_capture_shortcuts",
      { bindings: { ...defaults, selectedArea: "Control+Shift+KeyK" } },
    ],
  ]);
  expect(container.textContent).toContain("Ctrl + Shift + K");
  expect(container.textContent).toContain("saved and active");
  expect(document.activeElement).toBe(change());
});

it("accepts an existing OS-consumed chord through the native recorder event once", async () => {
  await mount();
  await begin("Whole Screen");
  await act(async () => {
    recorded({
      event: "capture-shortcut-recorded",
      id: 1,
      payload: defaults.selectedArea,
    });
    recorded({
      event: "capture-shortcut-recorded",
      id: 2,
      payload: defaults.selectedArea,
    });
  });
  expect(saves()).toHaveLength(1);
  expect(saves()[0][1]).toEqual({
    bindings: { ...defaults, wholeScreen: defaults.selectedArea },
  });
});

it("keeps displayed bindings when native registration rejects a conflict", async () => {
  const implementation = vi.mocked(invoke).getMockImplementation()!;
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "set_capture_shortcuts"
      ? Promise.reject(
          new Error("Shortcut unavailable. Choose another combination."),
        )
      : implementation(command, args),
  );
  await mount();
  await begin();
  await key("keydown", { key: "k", code: "KeyK", altKey: true });
  await key("keyup", { key: "k", code: "KeyK" });
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Shortcut unavailable",
  );
  expect(container.textContent).toContain("Ctrl + Shift + O");
  expect(change().disabled).toBe(false);
  expect(container.textContent).not.toContain("saved and active");
});

it("rejects typing, Shift-only, AltGraph and IME composition without saving", async () => {
  await mount();
  await begin();
  for (const options of [
    { key: "k", code: "KeyK" },
    { key: "K", code: "KeyK", shiftKey: true },
    { key: "Process", code: "KeyK", ctrlKey: true, isComposing: true },
    { key: " ", code: "Space", altKey: true },
  ])
    await key("keydown", options);
  await act(async () => {
    const event = new KeyboardEvent("keydown", {
      key: "k",
      code: "KeyK",
      ctrlKey: true,
      altKey: true,
    });
    vi.spyOn(event, "getModifierState").mockImplementation(
      (modifier) => modifier === "AltGraph",
    );
    window.dispatchEvent(event);
  });
  expect(saves()).toHaveLength(0);
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Use Ctrl",
  );
});

it.each(["Escape", "Tab"])("cancels recording with %s", async (name) => {
  await mount();
  await begin();
  await key("keydown", { key: name, code: name });
  expect(change().getAttribute("aria-pressed")).toBe("false");
  expect(invoke).toHaveBeenLastCalledWith("record_capture_shortcut", {
    recording: false,
  });
  expect(saves()).toHaveLength(0);
});

it("cancels on focus loss and category changes and cleans up its native listener", async () => {
  await mount();
  await begin();
  await act(async () => window.dispatchEvent(new Event("blur")));
  expect(change().getAttribute("aria-pressed")).toBe("false");
  await begin();
  await mount(false);
  expect(cleanup).toHaveBeenCalledTimes(1);
  expect(invoke).toHaveBeenLastCalledWith("record_capture_shortcut", {
    recording: false,
  });
  await mount();
  expect(change().getAttribute("aria-pressed")).toBe("false");
});

it("restores both defaults and displays startup availability warnings", async () => {
  const implementation = vi.mocked(invoke).getMockImplementation()!;
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "capture_shortcuts"
      ? Promise.resolve({
          ...initial,
          available: [false, true],
          warnings: ["Saved shortcut unavailable"],
          bindings: { ...defaults, selectedArea: "alt+KeyK" },
        })
      : implementation(command, args),
  );
  await mount();
  expect(container.textContent).toContain("Unavailable");
  expect(container.textContent).toContain("Saved shortcut unavailable");
  await act(async () =>
    Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent === "Restore defaults")!
      .click(),
  );
  expect(saves()[0][1]).toEqual({ bindings: defaults });
  expect(container.textContent).toContain("Default shortcuts restored");
});

it("does not leave controls busy when a save finishes after changing categories", async () => {
  const implementation = vi.mocked(invoke).getMockImplementation()!;
  let finish!: (value: typeof initial) => void;
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "set_capture_shortcuts"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : implementation(command, args),
  );
  await mount();
  await begin();
  await key("keydown", { key: "k", code: "KeyK", ctrlKey: true });
  await key("keyup", { key: "k", code: "KeyK" });
  await mount(false);
  await mount();
  await act(async () => finish(initial));
  expect(change().disabled).toBe(false);
});

it("disables recording when settings or the native event listener cannot load", async () => {
  vi.mocked(listen).mockRejectedValue(new Error("No event bridge"));
  await mount();
  expect(change().disabled).toBe(true);
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Could not start",
  );
});

it("cancels a pending recorder start when its category is hidden", async () => {
  const implementation = vi.mocked(invoke).getMockImplementation()!;
  let finish!: () => void;
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "record_capture_shortcut" &&
    (args as { recording: boolean }).recording
      ? new Promise<void>((resolve) => {
          finish = resolve;
        })
      : implementation(command, args),
  );
  await mount();
  await begin();
  await mount(false);
  await act(async () => finish());
  expect(invoke).toHaveBeenLastCalledWith("record_capture_shortcut", {
    recording: false,
  });
  await mount();
  expect(change().disabled).toBe(false);
  expect(change().getAttribute("aria-pressed")).toBe("false");
});

it("cleans up a native listener that resolves after the category was hidden", async () => {
  let finish!: (cleanup: () => void) => void;
  vi.mocked(listen).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await mount();
  await mount(false);
  await act(async () => finish(cleanup));
  expect(cleanup).toHaveBeenCalledOnce();
});

it("does not resume a pending recorder after focus leaves and returns", async () => {
  const implementation = vi.mocked(invoke).getMockImplementation()!;
  let finish!: () => void;
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "record_capture_shortcut" &&
    (args as { recording: boolean }).recording
      ? new Promise<void>((resolve) => {
          finish = resolve;
        })
      : implementation(command, args),
  );
  await mount();
  await begin();
  await act(async () => window.dispatchEvent(new Event("blur")));
  await act(async () => finish());
  expect(invoke).toHaveBeenLastCalledWith("record_capture_shortcut", {
    recording: false,
  });
  expect(change().getAttribute("aria-pressed")).toBe("false");
  expect(change().disabled).toBe(false);
});
