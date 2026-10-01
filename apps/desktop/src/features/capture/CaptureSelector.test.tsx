// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { requestOcr } from "../../lib/ocr-client";
import { CaptureSelector } from "./CaptureSelector";
import { loadScanArea, saveScanArea, type CaptureSurface } from "./scan-area";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ close: vi.fn().mockResolvedValue(undefined) }),
}));
vi.mock("../../lib/ocr-client", () => ({ requestOcr: vi.fn() }));

let container: HTMLDivElement;
let root: Root;
const captured = {
  imageDataUrl: "data:image/png;base64,AA==",
  metadata: {
    displayId: "display",
    displayName: "Display",
    screenPhysicalBounds: { x: 0, y: 0, width: 200, height: 100 },
    selectionPhysicalBounds: { x: 0, y: 0, width: 200, height: 100 },
    selectionLogicalBounds: { x: 0, y: 0, width: 200, height: 100 },
    imageWidth: 200,
    imageHeight: 100,
    scaleFactor: 1,
  },
};
const surface: CaptureSurface = {
  displayId: "display",
  screenPhysicalBounds: { x: 0, y: 0, width: 200, height: 100 },
  selectorPhysicalBounds: { x: 0, y: 0, width: 200, height: 100 },
  scaleFactor: 1,
};

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.history.replaceState({}, "", "/?mode=capture&scan=auto");
  window.localStorage.clear();
  Object.defineProperty(document.documentElement, "clientWidth", {
    configurable: true,
    value: 200,
  });
  Object.defineProperty(document.documentElement, "clientHeight", {
    configurable: true,
    value: 100,
  });
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    queueMicrotask(() => callback(0));
    return 1;
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  window.history.replaceState({}, "", "/");
  delete document.documentElement.dataset.capturing;
  vi.unstubAllGlobals();
  vi.mocked(invoke).mockReset();
  vi.mocked(requestOcr).mockReset();
});

it("uses the saved area when automatic page detection is uncertain", async () => {
  saveScanArea(surface, { x: 20, y: 10, width: 120, height: 70 });
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "capture_auto_page") return null;
    return command === "get_capture_surface" ? surface : captured;
  });
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(invoke).toHaveBeenCalledWith("capture_auto_page");
  expect(invoke).toHaveBeenCalledWith("get_capture_surface");
  expect(invoke).toHaveBeenCalledWith("capture_selection", {
    selection: { x: 20, y: 10, width: 120, height: 70 },
    viewport: { width: 200, height: 100 },
  });
  expect(requestOcr).toHaveBeenCalledExactlyOnceWith(
    "data:image/png;base64,AA==",
    { debug: false },
  );
  expect(container.textContent).toContain("No text was detected");
});

it("uses a detected page directly without consulting the saved area", async () => {
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(invoke).toHaveBeenCalledExactlyOnceWith("capture_auto_page");
  expect(requestOcr).toHaveBeenCalledTimes(1);
});

it("passes estimated reading order to the overlay for a page scan", async () => {
  const makeRegion = (id: string, x: number) => ({
    id,
    text: id,
    polygon: [
      { x, y: 10 },
      { x: x + 20, y: 10 },
      { x: x + 20, y: 60 },
      { x, y: 60 },
    ],
    orientation: "vertical" as const,
    confidence: 0,
    type: "dialogue" as const,
    tokens: [],
  });
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "capture_auto_page" ? captured : null,
  );
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [makeRegion("left", 20), makeRegion("right", 150)],
  });

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(invoke).toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.objectContaining({
      estimatedReadingOrder: true,
      regions: [
        expect.objectContaining({ id: "right" }),
        expect.objectContaining({ id: "left" }),
      ],
    }),
  );
});

it("asks for a scan area when none has been saved", async () => {
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "capture_auto_page" ? null : surface,
  );

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(container.textContent).toContain("Drag around the manga reading area");
  expect(container.textContent).toContain(
    "Automatic page detection was uncertain",
  );
  expect(invoke).not.toHaveBeenCalledWith(
    "capture_selection",
    expect.anything(),
  );
  expect(requestOcr).not.toHaveBeenCalled();
});

it("allows a manual retry when automatic capture fails", async () => {
  vi.mocked(invoke).mockRejectedValue(new Error("screen capture unavailable"));

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(container.textContent).toContain("screen capture unavailable");
  expect(container.textContent).toContain("Drag around the manga reading area");
});

it("saves a drawn reading area and captures only that selection", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=configure");
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "get_capture_surface" ? surface : captured,
  );
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  const selector =
    container.querySelector<HTMLDivElement>(".capture-selector")!;
  Object.defineProperty(selector, "clientWidth", { value: 200 });
  Object.defineProperty(selector, "clientHeight", { value: 100 });
  selector.setPointerCapture = vi.fn();
  await act(async () => {
    selector.dispatchEvent(
      new MouseEvent("pointerdown", {
        bubbles: true,
        clientX: 20,
        clientY: 10,
      }),
    );
  });
  await act(async () => {
    selector.dispatchEvent(
      new MouseEvent("pointerup", { bubbles: true, clientX: 140, clientY: 80 }),
    );
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(loadScanArea(surface)).toEqual({
    x: 20,
    y: 10,
    width: 120,
    height: 70,
  });
  expect(invoke).toHaveBeenCalledWith("capture_selection", {
    selection: { x: 20, y: 10, width: 120, height: 70 },
    viewport: { width: 200, height: 100 },
  });
});

it("does not turn an unavailable OCR demo into a scan-area click target", async () => {
  saveScanArea(surface, { x: 20, y: 10, width: 120, height: 70 });
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "capture_auto_page") return null;
    return command === "get_capture_surface" ? surface : captured;
  });
  vi.mocked(requestOcr).mockResolvedValue({ engine: "demo", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(container.textContent).toContain("needs the local OCR models");
  expect(invoke).not.toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.anything(),
  );
});
