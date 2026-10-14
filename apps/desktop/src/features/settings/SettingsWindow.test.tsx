// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { App } from "../../App";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
let container: HTMLDivElement;
let root: Root;
const status = { required: true, installed: false };
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.mocked(invoke).mockResolvedValue(status);
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

it("keeps a failed preference unchecked and retries without changing its stored key", async () => {
  window.history.replaceState({}, "", "/?view=reading");
  await mount();
  const setting = container.querySelector<HTMLInputElement>(
    'input[type="checkbox"]',
  )!;
  const save = vi
    .spyOn(Storage.prototype, "setItem")
    .mockImplementationOnce(() => {
      throw new Error("Storage unavailable");
    });
  await act(async () => setting.click());
  expect(setting.checked).toBe(false);
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Storage unavailable",
  );
  expect(
    window.localStorage.getItem("yomimado.reading-order.enabled.v1"),
  ).toBeNull();
  await act(async () => setting.click());
  expect(save).toHaveBeenCalledWith(
    "yomimado.reading-order.enabled.v1",
    "true",
  );
  expect(setting.checked).toBe(true);
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(container.textContent).toContain("Applies to new scans");
});

it("retries a status failure without claiming that the model is installed", async () => {
  vi.mocked(invoke).mockRejectedValueOnce(new Error("Status unavailable"));
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
  vi.mocked(invoke).mockImplementationOnce(
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
  vi.mocked(invoke)
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

it("preserves an installed detector after failed replacement and allows retry", async () => {
  vi.mocked(invoke)
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
  vi.mocked(invoke)
    .mockResolvedValueOnce(status)
    .mockImplementationOnce(
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
  vi.mocked(invoke).mockResolvedValue({ required: false, installed: false });
  await mount();
  expect(
    container.querySelector(".settings-model-status")?.textContent,
  ).toContain("development OCR service");
  expect(button("Select detector model file")).toBeUndefined();
  expect(container.textContent).toContain(
    "does not check whether that service is ready",
  );
});
