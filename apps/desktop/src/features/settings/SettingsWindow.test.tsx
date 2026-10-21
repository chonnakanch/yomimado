// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { App } from "../../App";

const detectorInvoke = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}));
const shortcuts = {
  bindings: {
    selectedArea: "control+shift+KeyO",
    wholeScreen: "control+shift+KeyS",
  },
  defaults: {
    selectedArea: "control+shift+KeyO",
    wholeScreen: "control+shift+KeyS",
  },
  available: [true, true],
  warnings: [],
};
let container: HTMLDivElement;
let root: Root;
const status = { required: true, installed: false };
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  detectorInvoke.mockResolvedValue(status);
  vi.mocked(invoke).mockImplementation((command, args) =>
    command === "capture_shortcuts"
      ? Promise.resolve(shortcuts)
      : command === "record_capture_shortcut"
        ? Promise.resolve(undefined)
        : detectorInvoke(command, args),
  );
  window.localStorage.clear();
  window.history.replaceState({}, "", "/?view=settings");
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
  detectorInvoke.mockReset();
});
const button = (label: string) =>
  Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find(
    (item) => item.textContent === label,
  )!;
const click = (label: string) => act(async () => button(label).click());
const mount = () => act(async () => root.render(<App />));

it("supports keyboard categories and opens Reading directly without checking the detector", async () => {
  window.history.replaceState({}, "", "/?view=reading");
  await mount();
  expect(invoke).not.toHaveBeenCalled();
  const reading = button("Reading");
  expect(reading.getAttribute("aria-selected")).toBe("true");
  await act(async () =>
    reading.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Home", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(button("Scan & OCR"));
  expect(button("Scan & OCR").tabIndex).toBe(0);
  expect(reading.tabIndex).toBe(-1);
  expect(
    container.querySelector<HTMLElement>("#settings-panel-reading")?.hidden,
  ).toBe(true);
  await act(async () =>
    button("Scan & OCR").dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    ),
  );
  expect(document.activeElement).toBe(reading);
  expect(button("About / Sources")).toBeUndefined();
  expect(invoke).toHaveBeenCalledWith("detector_model_status");
});

it("replaces the reading-order toggle with current keyboard-reading instructions", async () => {
  window.history.replaceState({}, "", "/?view=reading");
  window.localStorage.setItem("yomimado.reading-order.enabled.v1", "true");
  await mount();
  expect(
    container.querySelector('input[type="checkbox"]')?.parentElement
      ?.textContent,
  ).toContain("Show estimated JLPT levels");
  expect(container.textContent).toContain("More actions → Read with keyboard");
  expect(container.textContent).toContain("Arrow keys move between regions");
  expect(container.textContent).not.toContain("Focus regions");
  expect(invoke).not.toHaveBeenCalled();
});

it("retries a status failure without claiming that the model is installed", async () => {
  detectorInvoke.mockRejectedValueOnce(new Error("Status unavailable"));
  await mount();
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Status unavailable",
  );
  expect(button("Select detector model file")).toBeUndefined();
  await click("Refresh status");
  expect(button("Select detector model file").disabled).toBe(false);
  expect(container.querySelector('[role="alert"]')).toBeNull();
});

it("ignores an old status response after leaving and returning to Scan & OCR", async () => {
  let finish!: (value: typeof status) => void;
  detectorInvoke.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await mount();
  await click("Reading");
  await click("Scan & OCR");
  expect(button("Select detector model file").disabled).toBe(false);
  await act(async () => finish({ required: true, installed: true }));
  expect(button("Select detector model file").disabled).toBe(false);
  expect(button("Replace detector model")).toBeUndefined();
});

it("keeps the current detector when the file picker is canceled", async () => {
  detectorInvoke
    .mockResolvedValueOnce({ required: true, installed: true })
    .mockResolvedValueOnce(null);
  await mount();
  await click("Replace detector model");
  expect(invoke).toHaveBeenCalledWith("install_detector_model");
  expect(button("Replace detector model").disabled).toBe(false);
  expect(container.querySelector(".settings-model-status")?.textContent).toBe(
    "Installed on this computer.",
  );
  expect(container.querySelector(".settings-success")?.textContent).toBe("");
});

it("opens the detector release through the native browser launcher", async () => {
  await mount();
  const link = container.querySelector<HTMLAnchorElement>(
    'a[href="https://github.com/zyddnys/manga-image-translator/releases/latest"]',
  )!;
  const event = new MouseEvent("click", { bubbles: true, cancelable: true });
  await act(async () => link.dispatchEvent(event));
  expect(event.defaultPrevented).toBe(true);
  expect(invoke).toHaveBeenCalledWith("open_detector_release");
  expect(invoke).not.toHaveBeenCalledWith("install_detector_model");
});

it("reports browser launch failures and lets the detector release link retry", async () => {
  detectorInvoke
    .mockResolvedValueOnce(status)
    .mockRejectedValueOnce(new Error("No default browser"))
    .mockResolvedValueOnce(undefined);
  await mount();
  const link = container.querySelector<HTMLAnchorElement>("a")!;
  await act(async () => link.click());
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "No default browser",
  );
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Copy the link address",
  );
  expect(button("Select detector model file").disabled).toBe(false);
  await act(async () => link.click());
  expect(container.querySelector('[role="alert"]')).toBeNull();
});

it("preserves an installed detector after failed replacement and allows retry", async () => {
  detectorInvoke
    .mockResolvedValueOnce({ required: true, installed: true })
    .mockRejectedValueOnce(
      new Error(
        "The selected file does not match the supported detector model.",
      ),
    )
    .mockResolvedValueOnce({ required: true, installed: true });
  await mount();
  await click("Replace detector model");
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "does not match",
  );
  expect(container.querySelector(".settings-model-status")?.textContent).toBe(
    "Installed on this computer.",
  );
  await click("Replace detector model");
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(container.querySelector(".settings-success")?.textContent).toContain(
    "Restart YomiMado",
  );
});

it("blocks duplicate imports and retains pending state across category changes", async () => {
  let finish!: (value: typeof status) => void;
  detectorInvoke.mockResolvedValueOnce(status).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await mount();
  await act(async () => {
    button("Select detector model file").click();
    button("Select detector model file").click();
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([command]) => command === "install_detector_model"),
  ).toHaveLength(1);
  expect(button("Refresh status").disabled).toBe(true);
  await click("Reading");
  await click("Scan & OCR");
  expect(button("Checking model…").disabled).toBe(true);
  await act(async () => finish({ required: true, installed: true }));
  expect(button("Replace detector model").disabled).toBe(false);
});

it("keeps development model setup distinct from packaged installation", async () => {
  detectorInvoke.mockResolvedValue({ required: false, installed: false });
  await mount();
  expect(
    container.querySelector(".settings-model-status")?.textContent,
  ).toContain("development OCR service");
  expect(button("Select detector model file")).toBeUndefined();
  expect(container.textContent).toContain(
    "does not check whether that service is ready",
  );
});
