// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { requestOcr } from "../../lib/ocr-client";
import { CaptureSelector } from "./CaptureSelector";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
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

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.history.replaceState({}, "", "/?mode=capture&scan=display");
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

it("captures the display once without a drag and reports no OCR regions", async () => {
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });

  expect(invoke).toHaveBeenCalledExactlyOnceWith("capture_display");
  expect(requestOcr).toHaveBeenCalledExactlyOnceWith(
    "data:image/png;base64,AA==",
    { debug: false },
  );
  expect(container.textContent).toContain("No text was detected");
});

it("does not turn an unavailable OCR demo into a full-screen click target", async () => {
  vi.mocked(invoke).mockResolvedValue(captured);
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
