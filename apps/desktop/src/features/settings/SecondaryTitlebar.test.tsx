// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { SecondaryTitlebar } from "./SecondaryTitlebar";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
let container: HTMLDivElement;
let root: Root;
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.mocked(invoke).mockResolvedValue(undefined);
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.mocked(invoke).mockReset();
});
const button = (label: string) =>
  container.querySelector<HTMLButtonElement>(`[aria-label="${label}"]`)!;

it("uses hide for the accessible Close action without requesting native close or Quit", async () => {
  await act(async () => root.render(<SecondaryTitlebar />));
  await act(async () => button("Close window").click());
  expect(invoke).toHaveBeenCalledExactlyOnceWith("control_secondary_window", {
    action: "hide",
  });
  expect(button("Close window").getAttribute("title")).toContain(
    "keep YomiMado running",
  );
  expect(container.querySelector('[role="alert"]')).toBeNull();
});

it("reports a failed hide and permits closing again without claiming success", async () => {
  vi.mocked(invoke).mockRejectedValueOnce(new Error("Window is unavailable"));
  await act(async () => root.render(<SecondaryTitlebar />));
  await act(async () => button("Close window").click());
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Unable to close this window",
  );
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Window is unavailable",
  );
  await act(async () => button("Close window").click());
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(invoke).toHaveBeenCalledTimes(2);
});

it("keeps control clicks separate from dragging and supports minimize and restore", async () => {
  await act(async () => root.render(<SecondaryTitlebar />));
  await act(async () => button("Minimize window").click());
  await act(async () => button("Maximize or restore window").click());
  expect(vi.mocked(invoke).mock.calls).toEqual([
    ["control_secondary_window", { action: "minimize" }],
    ["control_secondary_window", { action: "toggleMaximize" }],
  ]);
  const handle = container.querySelector<HTMLElement>(
    ".secondary-drag-handle",
  )!;
  await act(async () =>
    handle.dispatchEvent(
      new MouseEvent("mousedown", { button: 2, bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenCalledTimes(2);
  await act(async () =>
    handle.dispatchEvent(
      new MouseEvent("mousedown", { button: 0, bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenLastCalledWith("control_secondary_window", {
    action: "drag",
  });
});
