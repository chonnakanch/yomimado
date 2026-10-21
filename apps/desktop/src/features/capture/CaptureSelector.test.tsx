// @vitest-environment jsdom
import { act, StrictMode } from "react";
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

function mockPointerCapture(selector: HTMLDivElement) {
  const pointers = new Set<number>();
  selector.setPointerCapture = vi.fn((id: number) => pointers.add(id));
  selector.hasPointerCapture = vi.fn((id: number) => pointers.has(id));
  selector.releasePointerCapture = vi.fn((id: number) => pointers.delete(id));
}

async function pointer(
  selector: HTMLDivElement,
  type: string,
  options: MouseEventInit & { pointerId?: number } = {},
) {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    button: 0,
    buttons: type === "pointerup" ? 0 : 1,
    clientX: 20,
    clientY: 10,
    ...options,
  });
  Object.defineProperty(event, "pointerId", { value: options.pointerId ?? 1 });
  await act(async () => {
    selector.dispatchEvent(event);
  });
}

async function manualSelector(mode = "selected") {
  window.history.replaceState(
    {},
    "",
    `/?mode=capture&session=50${mode === "selected" ? "" : `&scan=${mode}`}`,
  );
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "capture_whole_screen"
      ? null
      : command === "get_capture_surface"
        ? surface
        : command === "capture_selection"
          ? captured
          : undefined,
  );
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });
  await act(async () => root.render(<CaptureSelector />));
  const selector =
    container.querySelector<HTMLDivElement>(".capture-selector")!;
  Object.defineProperty(selector, "clientWidth", { value: 200 });
  Object.defineProperty(selector, "clientHeight", { value: 100 });
  mockPointerCapture(selector);
  return selector;
}

async function expectFreshDrag(selector: HTMLDivElement) {
  await pointer(selector, "pointerdown");
  await pointer(selector, "pointermove", { clientX: 100, clientY: 60 });
  await pointer(selector, "pointerup", { clientX: 140, clientY: 80 });
  expect(invoke).toHaveBeenCalledWith("capture_selection", {
    sessionId: 50,
    selection: { x: 20, y: 10, width: 120, height: 70 },
    viewport: { width: 200, height: 100 },
  });
  expect(requestOcr).toHaveBeenCalledOnce();
}

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
  vi.unstubAllEnvs();
  vi.mocked(invoke).mockReset();
  vi.mocked(requestOcr).mockReset();
  vi.useRealTimers();
});

it("continues automatic capture when a hidden WebView suspends animation frames", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", () => 1);
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

  await act(async () => root.render(<CaptureSelector />));
  expect(invoke).not.toHaveBeenCalledWith("capture_auto_page");
  await act(async () => {
    await vi.advanceTimersByTimeAsync(100);
  });

  expect(invoke).toHaveBeenCalledExactlyOnceWith("capture_auto_page");
  expect(requestOcr).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("No text was detected");
  expect(document.documentElement.dataset.capturing).toBe("false");
});

it("publishes a first Whole Screen scan once under StrictMode without a prior manual selection or animation frame", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", () => 1);
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=41");
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "capture_whole_screen" ? captured : undefined,
  );
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [
      {
        id: "first",
        text: "今日",
        polygon: [
          { x: 10, y: 10 },
          { x: 30, y: 10 },
          { x: 30, y: 70 },
          { x: 10, y: 70 },
        ],
        orientation: "vertical",
        confidence: 0,
        type: "dialogue",
        tokens: [],
      },
    ],
  });
  await act(async () =>
    root.render(
      <StrictMode>
        <CaptureSelector />
      </StrictMode>,
    ),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(100);
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([command]) => command === "capture_whole_screen"),
  ).toEqual([["capture_whole_screen", { sessionId: 41 }]]);
  expect(requestOcr).toHaveBeenCalledOnce();
  expect(invoke).toHaveBeenCalledWith("hide_finished_selector", {
    sessionId: 41,
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([command]) => command === "report_ocr_stage")
      .map(([, args]) => args),
  ).toEqual([
    { sessionId: 41, stage: "requesting" },
    { sessionId: 41, stage: "recognized" },
    { sessionId: 41, stage: "publishing" },
  ]);
  expect(invoke).not.toHaveBeenCalledWith(
    "capture_selection",
    expect.anything(),
  );
});

it("ends the Whole Screen session with an error when recognition times out", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=42");
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockRejectedValue(
    new Error(
      "OCR timed out after 3 minutes. Check the local OCR service and try again.",
    ),
  );
  await act(async () => root.render(<CaptureSelector />));
  expect(invoke).toHaveBeenCalledWith("finish_scan", {
    sessionId: 42,
    message: expect.stringContaining("OCR timed out"),
  });
  expect(invoke).not.toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.anything(),
  );
  expect(document.documentElement.dataset.capturing).toBe("false");
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

  expect(container.textContent).toContain("Drag around pages");
  expect(container.querySelector(".capture-edge-hint")).not.toBeNull();
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
  expect(container.textContent).toContain("Drag around pages");
});

it.each(["configure", "whole"])(
  "saves a drawn reading area after %s and captures only that selection",
  async (mode) => {
    window.history.replaceState({}, "", `/?mode=capture&scan=${mode}`);
    vi.mocked(invoke).mockImplementation(async (command) =>
      command === "capture_whole_screen"
        ? null
        : command === "get_capture_surface"
          ? surface
          : captured,
    );
    vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });

    await act(async () => root.render(<CaptureSelector />));
    const selector =
      container.querySelector<HTMLDivElement>(".capture-selector")!;
    Object.defineProperty(selector, "clientWidth", { value: 200 });
    Object.defineProperty(selector, "clientHeight", { value: 100 });
    mockPointerCapture(selector);
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
        new MouseEvent("pointerup", {
          bubbles: true,
          clientX: 140,
          clientY: 80,
        }),
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
  },
);

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

it("sends only the detected Whole Screen page to OCR and preserves its crop metadata", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=12");
  const page = {
    imageDataUrl: "data:image/png;base64,AQ==",
    metadata: {
      ...captured.metadata,
      selectionPhysicalBounds: { x: 20, y: 10, width: 120, height: 70 },
      selectionLogicalBounds: { x: 20, y: 10, width: 120, height: 70 },
      imageWidth: 120,
      imageHeight: 70,
    },
  };
  vi.mocked(invoke).mockResolvedValue(page);
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [
      {
        id: "page-text",
        text: "今日",
        polygon: [
          { x: 10, y: 10 },
          { x: 30, y: 10 },
          { x: 30, y: 50 },
        ],
        orientation: "vertical",
        confidence: 0,
        type: "dialogue",
        tokens: [],
      },
    ],
  });
  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });
  expect(invoke).toHaveBeenCalledWith("capture_whole_screen", {
    sessionId: 12,
  });
  expect(invoke).not.toHaveBeenCalledWith(
    "capture_auto_page",
    expect.anything(),
  );
  expect(requestOcr).toHaveBeenCalledExactlyOnceWith(page.imageDataUrl, {
    debug: false,
  });
  expect(invoke).toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.objectContaining({
      sessionId: 12,
      metadata: page.metadata,
      estimatedReadingOrder: true,
    }),
  );
  expect(invoke).not.toHaveBeenCalledWith(
    "get_capture_surface",
    expect.anything(),
  );
});

it("uses the saved manga area when Whole Screen cannot confidently find a page", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=13");
  saveScanArea(surface, { x: 20, y: 10, width: 120, height: 70 });
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "capture_whole_screen"
      ? null
      : command === "get_capture_surface"
        ? surface
        : captured,
  );
  vi.mocked(requestOcr).mockResolvedValue({ engine: "manga", regions: [] });
  await act(async () => root.render(<CaptureSelector />));
  expect(invoke).toHaveBeenCalledWith("capture_selection", {
    sessionId: 13,
    selection: { x: 20, y: 10, width: 120, height: 70 },
    viewport: { width: 200, height: 100 },
  });
  expect(requestOcr).toHaveBeenCalledOnce();
});

it.each([null, { x: -50, y: 0, width: 120, height: 70 }])(
  "asks for a manga area without OCR when Whole Screen is uncertain and the saved area is %j",
  async (area) => {
    window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=14");
    if (area) saveScanArea(surface, area);
    vi.mocked(invoke).mockImplementation(async (command) =>
      command === "capture_whole_screen"
        ? null
        : command === "get_capture_surface"
          ? surface
          : undefined,
    );
    await act(async () => root.render(<CaptureSelector />));
    expect(container.querySelector(".capture-edge-hint")).not.toBeNull();
    expect(container.textContent).toContain("Drag around pages");
    expect(invoke).toHaveBeenCalledWith("resume_capture_selection", {
      sessionId: 14,
      debug: false,
    });
    expect(invoke).not.toHaveBeenCalledWith(
      "capture_selection",
      expect.anything(),
    );
    expect(requestOcr).not.toHaveBeenCalled();
  },
);

it("Rescan captures new pixels and retains its session ID through OCR publication", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=repeat&session=15");
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [
      {
        id: "one",
        text: "今日",
        polygon: [
          { x: 1, y: 1 },
          { x: 20, y: 1 },
          { x: 20, y: 40 },
        ],
        orientation: "vertical",
        confidence: 0,
        type: "other",
        tokens: [],
      },
    ],
  });
  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });
  expect(invoke).toHaveBeenCalledWith("capture_repeat_scan", { sessionId: 15 });
  expect(requestOcr).toHaveBeenCalledOnce();
  expect(invoke).toHaveBeenCalledWith("hide_finished_selector", {
    sessionId: 15,
  });
  expect(invoke).toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.objectContaining({
      sessionId: 15,
      metadata: captured.metadata,
      regions: [expect.objectContaining({ text: "今日" })],
    }),
  );
});

it("retains optional estimated navigation when repeating a page or Whole Screen scan", async () => {
  window.history.replaceState(
    {},
    "",
    "/?mode=capture&scan=repeat&order=1&session=16",
  );
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [
      {
        id: "one",
        text: "今日",
        polygon: [
          { x: 1, y: 1 },
          { x: 20, y: 1 },
          { x: 20, y: 40 },
        ],
        orientation: "vertical",
        confidence: 0,
        type: "other",
        tokens: [],
      },
    ],
  });
  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });
  expect(invoke).toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.objectContaining({ estimatedReadingOrder: true, sessionId: 16 }),
  );
});

it("reports a failed capture to the toolbar instead of leaving a hidden selector busy", async () => {
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=21");
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "capture_whole_screen")
      throw new Error("display disconnected");
    return undefined;
  });
  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });
  expect(requestOcr).not.toHaveBeenCalled();
  expect(invoke).toHaveBeenCalledWith("finish_scan", {
    sessionId: 21,
    message: expect.stringContaining("display disconnected"),
  });
});

it("keeps the developer capture preview accessible when OCR fails", async () => {
  vi.stubEnv("VITE_CAPTURE_DEBUG", "1");
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=24");
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockRejectedValue(
    new Error("local models unavailable"),
  );
  await act(async () => root.render(<CaptureSelector />));
  await act(async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  });
  expect(container.querySelector(".capture-debug")).not.toBeNull();
  expect(container.textContent).toContain("local models unavailable");
  expect(invoke).toHaveBeenCalledWith("resume_capture_selection", {
    sessionId: 24,
    debug: true,
  });
  expect(invoke).not.toHaveBeenCalledWith("finish_scan", expect.anything());
});

it("holds successful debug OCR for review until Show overlay is explicitly activated", async () => {
  vi.stubEnv("VITE_CAPTURE_DEBUG", "1");
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
  window.history.replaceState({}, "", "/?mode=capture&scan=whole&session=25");
  vi.mocked(invoke).mockResolvedValue(captured);
  vi.mocked(requestOcr).mockResolvedValue({
    engine: "manga",
    regions: [
      {
        id: "debug",
        text: "今日",
        polygon: [
          { x: 10, y: 10 },
          { x: 30, y: 10 },
          { x: 30, y: 60 },
        ],
        orientation: "vertical",
        confidence: 0,
        type: "dialogue",
        tokens: [],
      },
    ],
  });
  await act(async () => root.render(<CaptureSelector />));
  expect(container.querySelector(".capture-debug")?.textContent).toContain(
    "今日",
  );
  expect(requestOcr).toHaveBeenCalledExactlyOnceWith(captured.imageDataUrl, {
    debug: true,
  });
  expect(invoke).toHaveBeenCalledWith("resume_capture_selection", {
    sessionId: 25,
    debug: true,
  });
  expect(invoke).not.toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.anything(),
  );
  const show = Array.from(container.querySelectorAll("button")).find(
    (button) => button.textContent === "Show overlay",
  )!;
  expect(show.disabled).toBe(false);
  await act(async () => show.click());
  expect(invoke).toHaveBeenCalledWith(
    "show_ocr_overlay",
    expect.objectContaining({
      sessionId: 25,
      regions: [expect.objectContaining({ text: "今日" })],
    }),
  );
});

it.each(["whole", "selected"])(
  "allows a drag through the %s edge hint, hides it during selection and cancels with Escape",
  async (mode) => {
    window.history.replaceState(
      {},
      "",
      `/?mode=capture&${mode === "whole" ? "scan=whole&" : ""}session=30`,
    );
    vi.mocked(invoke).mockImplementation(async (command) =>
      command === "capture_whole_screen"
        ? null
        : command === "get_capture_surface"
          ? surface
          : undefined,
    );
    await act(async () => root.render(<CaptureSelector />));
    const selector =
      container.querySelector<HTMLDivElement>(".capture-selector")!;
    mockPointerCapture(selector);
    const hint = container.querySelector<HTMLElement>(".capture-edge-hint")!;
    const guidance = container.querySelector<HTMLElement>(
      ".capture-edge-guidance",
    )!;
    expect(hint.textContent).toBe(
      `${mode === "whole" ? "Drag around pages" : "Drag to capture"}Esc cancel`,
    );
    expect(container.querySelector(".capture-guidance")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
    expect(container.querySelector('[role="alert"]')).toBeNull();
    await act(async () =>
      hint.dispatchEvent(
        new MouseEvent("pointerdown", {
          bubbles: true,
          clientX: 20,
          clientY: 20,
        }),
      ),
    );
    expect(selector.setPointerCapture).toHaveBeenCalledOnce();
    expect(guidance.style.visibility).toBe("hidden");
    expect(container.querySelector(".selection")).not.toBeNull();
    await act(async () =>
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
    );
    expect(invoke).toHaveBeenCalledWith("cancel_capture_selector", {
      sessionId: 30,
    });
    expect(requestOcr).not.toHaveBeenCalled();
    await act(async () =>
      selector.dispatchEvent(new Event("pointercancel", { bubbles: true })),
    );
    expect(guidance.style.visibility).toBe("");
    expect(container.querySelector(".selection")).toBeNull();
  },
);

it.each([
  { mode: "selected", button: 2, buttons: 2, ctrlKey: false },
  { mode: "selected", button: 1, buttons: 4, ctrlKey: false },
  { mode: "selected", button: 0, buttons: 1, ctrlKey: true },
  { mode: "whole", button: 2, buttons: 2, ctrlKey: false },
  { mode: "configure", button: 2, buttons: 2, ctrlKey: false },
])(
  "ignores secondary/context clicks in $mode (button $button, control $ctrlKey) and allows a fresh drag",
  async ({ mode, button, buttons, ctrlKey }) => {
    const selector = await manualSelector(mode);
    await pointer(selector, "pointerdown", { button, buttons, ctrlKey });
    const contextMenu = new MouseEvent("contextmenu", {
      bubbles: true,
      cancelable: true,
      button: 2,
    });
    await act(async () => {
      selector.dispatchEvent(contextMenu);
    });
    await pointer(selector, "pointerup", {
      button,
      clientX: 140,
      clientY: 80,
    });
    expect(contextMenu.defaultPrevented).toBe(true);
    expect(selector.setPointerCapture).not.toHaveBeenCalled();
    expect(container.querySelector(".selection")).toBeNull();
    expect(requestOcr).not.toHaveBeenCalled();
    await expectFreshDrag(selector);
  },
);

it.each(["selected", "whole", "configure"])(
  "recovers from a right click while dragging in %s without capturing on secondary release",
  async (mode) => {
    const selector = await manualSelector(mode);
    await pointer(selector, "pointerdown");
    await pointer(selector, "pointermove", { clientX: 100, clientY: 60 });
    expect(container.querySelector(".selection")).not.toBeNull();
    // Browsers emit pointermove for additional button presses/releases.
    await pointer(selector, "pointermove", { button: 2, buttons: 3 });
    expect(selector.releasePointerCapture).toHaveBeenCalledWith(1);
    expect(container.querySelector(".selection")).toBeNull();
    expect(
      container.querySelector<HTMLElement>(".capture-edge-guidance")!.style
        .visibility,
    ).toBe("");
    await pointer(selector, "pointermove", { button: 0, buttons: 2 });
    await pointer(selector, "pointerup", {
      button: 2,
      clientX: 140,
      clientY: 80,
    });
    expect(requestOcr).not.toHaveBeenCalled();
    await expectFreshDrag(selector);
  },
);

it("suppresses a context menu during a drag and permits the next selection", async () => {
  const selector = await manualSelector();
  await pointer(selector, "pointerdown");
  await pointer(selector, "pointermove", { clientX: 100, clientY: 60 });
  const contextMenu = new MouseEvent("contextmenu", {
    bubbles: true,
    cancelable: true,
  });
  await act(async () => {
    selector.dispatchEvent(contextMenu);
  });
  expect(contextMenu.defaultPrevented).toBe(true);
  expect(container.querySelector(".selection")).toBeNull();
  expect(selector.releasePointerCapture).toHaveBeenCalledWith(1);
  await pointer(selector, "pointerup", { clientX: 140, clientY: 80 });
  expect(requestOcr).not.toHaveBeenCalled();
  await expectFreshDrag(selector);
});

it.each(["pointercancel", "lostpointercapture"])(
  "clears an interrupted drag on %s and ignores late releases",
  async (type) => {
    const selector = await manualSelector();
    await pointer(selector, "pointerdown");
    await pointer(selector, "pointermove", { clientX: 100, clientY: 60 });
    await pointer(selector, type, { pointerId: 2 });
    expect(container.querySelector(".selection")).not.toBeNull();
    await pointer(selector, type);
    expect(container.querySelector(".selection")).toBeNull();
    await pointer(selector, "pointerup", { clientX: 140, clientY: 80 });
    expect(requestOcr).not.toHaveBeenCalled();
    await expectFreshDrag(selector);
  },
);

it("ignores other pointers and clears a too-small drag before retrying", async () => {
  const selector = await manualSelector();
  await pointer(selector, "pointerdown");
  await pointer(selector, "pointerdown", { pointerId: 2 });
  await pointer(selector, "pointermove", {
    pointerId: 2,
    clientX: 100,
    clientY: 60,
  });
  await pointer(selector, "pointerup", {
    pointerId: 2,
    clientX: 140,
    clientY: 80,
  });
  expect(requestOcr).not.toHaveBeenCalled();
  await pointer(selector, "pointerup");
  expect(container.querySelector(".selection")).toBeNull();
  await pointer(selector, "pointerup", { clientX: 140, clientY: 80 });
  expect(requestOcr).not.toHaveBeenCalled();
  await expectFreshDrag(selector);
});
