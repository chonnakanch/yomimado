// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import {
  bubbleTranslationPreferenceKey,
  setBubbleTranslationEnabled,
  setBubbleTranslationFontSize,
} from "./bubble-translation-preference";
import { listen } from "@tauri-apps/api/event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { OcrOverlay } from "./OcrOverlay";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(vi.fn()),
}));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  window.localStorage.clear();
  window.history.replaceState({}, "", "/index.html?mode=overlay");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  window.history.replaceState({}, "", "/");
  vi.mocked(invoke).mockReset();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const completedOverlay = {
  sessionId: 42,
  metadata: {
    displayId: "left",
    displayName: "Left display",
    screenPhysicalBounds: { x: -1920, y: 0, width: 1920, height: 1080 },
    selectionPhysicalBounds: { x: -1800, y: 100, width: 640, height: 480 },
    selectionLogicalBounds: { x: -900, y: 50, width: 320, height: 240 },
    imageWidth: 640,
    imageHeight: 480,
    scaleFactor: 2,
  },
  regions: [],
  engine: "manga",
  layout: {
    windowWidth: 640,
    windowHeight: 544,
    contentLeft: 0,
    contentTop: 32,
    contentWidth: 320,
    contentHeight: 240,
    toolbarTop: 0,
    toolbarHeight: 32,
  },
};

it("shows a small hide control only after reveal and reports measured native hit bounds", async () => {
  vi.stubGlobal("innerWidth", 320);
  vi.stubGlobal("innerHeight", 272);
  window.history.replaceState({}, "", "/index.html?mode=overlay&session=42");
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    x: 290,
    y: 2,
    left: 290,
    top: 2,
    right: 318,
    bottom: 30,
    width: 28,
    height: 28,
    toJSON: () => ({}),
  });
  let reveal!: (value: typeof completedOverlay.layout) => void;
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_overlay_state") return completedOverlay;
    if (command === "reveal_ocr_overlay")
      return new Promise((resolve) => {
        reveal = resolve;
      });
    return undefined;
  });
  await act(async () => root.render(<OcrOverlay />));
  expect(
    container.querySelector('[aria-label="Hide OCR overlays"]'),
  ).toBeNull();
  await act(async () => reveal(completedOverlay.layout));
  const hide = container.querySelector<HTMLButtonElement>(
    '[aria-label="Hide OCR overlays"]',
  )!;
  expect(hide.title).toBe("Hide OCR overlays (Esc)");
  expect(hide.getAttribute("aria-keyshortcuts")).toBe("Escape");
  expect(invoke).toHaveBeenCalledWith("update_overlay_controls", {
    sessionId: 42,
    revision: 1,
    rectangles: [{ x: 290, y: 2, width: 28, height: 28 }],
    viewportWidth: 320,
    viewportHeight: 272,
    viewQuery: "mode=overlay&session=42",
  });
  await act(async () => hide.click());
  expect(invoke).toHaveBeenCalledWith("hide_completed_ocr_overlay", {
    sessionId: 42,
  });
});

it("keeps the hide control usable after failure and blocks duplicate pending requests", async () => {
  let fail!: (reason: Error) => void;
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_overlay_state") return completedOverlay;
    if (command === "reveal_ocr_overlay") return completedOverlay.layout;
    if (command === "hide_completed_ocr_overlay")
      return new Promise((_resolve, reject) => {
        fail = reject;
      });
    return undefined;
  });
  await act(async () => root.render(<OcrOverlay />));
  const hide = container.querySelector<HTMLButtonElement>(
    '[aria-label="Hide OCR overlays"]',
  )!;
  await act(async () => {
    hide.click();
    hide.click();
  });
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([c]) => c === "hide_completed_ocr_overlay"),
  ).toHaveLength(1);
  expect(hide.disabled).toBe(true);
  await act(async () => fail(new Error("Window unavailable")));
  expect(container.textContent).toContain("Could not hide OCR overlays");
  expect(hide.disabled).toBe(false);
});

it.each([false, true])(
  "loads OCR from native state, preserving accessible review labels with debug tooltips enabled=%s",
  async (debug) => {
    vi.stubEnv("VITE_CAPTURE_DEBUG", debug ? "1" : "0");
    const regions = Array.from({ length: 300 }, (_, index) => ({
      id: `region-${index}`,
      text: "日本語の長い文章".repeat(20),
      polygon: [
        { x: 10, y: 10 },
        { x: 30, y: 10 },
        { x: 30, y: 40 },
        { x: 10, y: 40 },
      ],
      orientation: "vertical",
      confidence: 0,
      type: "dialogue",
      tokens: [],
      ...(index === 0
        ? {
            needsReview: true,
            reviewReason: "Short text from detector mask; verify on page",
          }
        : {}),
      ...(index === 1
        ? {
            geometrySource: "expandedCrop",
            needsReview: true,
            reviewReason: "Expanded short vertical crop; area approximate",
          }
        : {}),
    }));
    vi.mocked(invoke).mockResolvedValue({
      metadata: {
        displayId: "display",
        displayName: "Display",
        screenPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        selectionPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        selectionLogicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        imageWidth: 1000,
        imageHeight: 800,
        scaleFactor: 1,
      },
      regions,
      engine: "manga",
      layout: {
        windowWidth: 1000,
        windowHeight: 800,
        contentLeft: 0,
        contentTop: 0,
        contentWidth: 1000,
        contentHeight: 800,
        toolbarTop: 0,
        toolbarHeight: 32,
      },
    });

    await act(async () => root.render(<OcrOverlay />));

    expect(invoke).toHaveBeenCalledExactlyOnceWith("get_overlay_state");
    expect(container.querySelectorAll("polygon.ocr-region")).toHaveLength(300);
    const reviewRegion = container.querySelector(
      "polygon.ocr-region.needs-review",
    );
    expect(reviewRegion).not.toBeNull();
    if (debug)
      expect(reviewRegion?.querySelector("title")?.textContent).toContain(
        "verify on page",
      );
    else expect(container.querySelector("polygon title")).toBeNull();
    expect(reviewRegion?.getAttribute("aria-label")).toContain("Review OCR");
    expect(
      container
        .querySelector("polygon.approximate")
        ?.getAttribute("aria-label"),
    ).toContain("Approximate region");
    expect(container.querySelector(".overlay-reading-order-panel")).toBeNull();
    expect(
      container.querySelectorAll("polygon.ocr-region.approximate"),
    ).toHaveLength(1);
    expect(window.location.search).toBe("?mode=overlay");

    await act(async () => {
      reviewRegion?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(invoke).toHaveBeenCalledWith(
      "show_translation_popup",
      expect.objectContaining({ text: regions[0].text }),
    );
  },
);

it("mounts the current polygons before revealing a reused native overlay", async () => {
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "reveal_ocr_overlay") {
      expect(container.querySelectorAll("polygon.ocr-region")).toHaveLength(1);
      expect(
        container
          .querySelector("polygon.ocr-region")
          ?.getAttribute("aria-label"),
      ).toContain("今日");
      return {
        windowWidth: 1000,
        windowHeight: 800,
        contentLeft: 0,
        contentTop: 0,
        contentWidth: 1000,
        contentHeight: 800,
        toolbarTop: 0,
        toolbarHeight: 32,
      };
    }
    return {
      sessionId: 90,
      metadata: {
        displayId: "display",
        displayName: "Display",
        screenPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        selectionPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        selectionLogicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
        imageWidth: 1000,
        imageHeight: 800,
        scaleFactor: 1,
      },
      regions: [
        {
          id: "current",
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
      engine: "manga",
      layout: {
        windowWidth: 1000,
        windowHeight: 800,
        contentLeft: 0,
        contentTop: 0,
        contentWidth: 1000,
        contentHeight: 800,
        toolbarTop: 0,
        toolbarHeight: 32,
      },
    };
  });
  await act(async () => root.render(<OcrOverlay />));
  expect(invoke).toHaveBeenCalledWith("reveal_ocr_overlay", { sessionId: 90 });
});

it("replaces the old reading panel without auto-selecting or stealing focus", async () => {
  window.localStorage.setItem("yomimado.reading-order.enabled.v1", "true");
  const metadata = {
    displayId: "display",
    displayName: "Display",
    screenPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
    selectionPhysicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
    selectionLogicalBounds: { x: 0, y: 0, width: 1000, height: 800 },
    imageWidth: 1000,
    imageHeight: 800,
    scaleFactor: 1,
  };
  const regions = ["right", "left"].map((text, index) => ({
    id: text,
    text: index === 0 ? "短い" : "これは長い文章ですがボタンは動きません",
    polygon: [
      { x: index * 100, y: 10 },
      { x: index * 100 + 40, y: 10 },
      { x: index * 100 + 40, y: 90 },
      { x: index * 100, y: 90 },
    ],
    orientation: "vertical",
    confidence: 0,
    type: "dialogue",
    tokens: [],
  }));
  vi.mocked(invoke).mockResolvedValue({
    metadata,
    regions,
    engine: "manga",
    estimatedReadingOrder: true,
    layout: {
      windowWidth: 1000,
      windowHeight: 800,
      contentLeft: 0,
      contentTop: 0,
      contentWidth: 1000,
      contentHeight: 800,
      toolbarTop: 0,
      toolbarHeight: 32,
    },
  });

  await act(async () => root.render(<OcrOverlay />));
  expect(container.querySelector(".overlay-reading-order-panel")).toBeNull();
  expect(container.querySelector("polygon.ocr-region.active")).toBeNull();

  expect(document.activeElement).toBe(document.body);
  expect(container.querySelectorAll("button")).toHaveLength(0);
});

it("opens only on explicit activation and provides keyboard navigation and hide", async () => {
  let onFocus:
    ((event: { payload: { regionId: string | null } }) => void) | undefined;
  const unlisten = vi.fn();
  vi.mocked(listen).mockImplementation(async (_name, callback) => {
    if (_name === "focus-ocr-region") {
      onFocus = callback as typeof onFocus;
      return unlisten;
    }
    return () => {};
  });
  const metadata = {
    displayId: "left",
    displayName: "Left",
    screenPhysicalBounds: { x: -1000, y: 0, width: 1000, height: 800 },
    selectionPhysicalBounds: { x: -1000, y: 0, width: 1000, height: 800 },
    selectionLogicalBounds: { x: -1000, y: 0, width: 1000, height: 800 },
    imageWidth: 1000,
    imageHeight: 800,
    scaleFactor: 1,
  };
  const regions = ["今日", "学校"].map((text, index) => ({
    id: String(index),
    text,
    polygon: [
      { x: 10 + index * 100, y: 10 },
      { x: 60 + index * 100, y: 10 },
      { x: 60 + index * 100, y: 100 },
      { x: 10 + index * 100, y: 100 },
    ],
    orientation: "vertical",
    confidence: 0,
    type: "dialogue",
    tokens: [],
  }));
  vi.mocked(invoke).mockResolvedValue({
    metadata,
    regions,
    engine: "manga",
    layout: {
      windowWidth: 1000,
      windowHeight: 800,
      contentLeft: 0,
      contentTop: 0,
      contentWidth: 1000,
      contentHeight: 800,
      toolbarTop: 0,
      toolbarHeight: 32,
    },
  });
  await act(async () => root.render(<OcrOverlay />));
  const polygons = Array.from(
    container.querySelectorAll<SVGPolygonElement>("polygon.ocr-region"),
  );
  const focusFirst = vi.fn();
  const focusLast = vi.fn();
  Object.defineProperty(polygons[0], "focus", { value: focusFirst });
  Object.defineProperty(polygons[1], "focus", { value: focusLast });
  expect(polygons[0].getAttribute("role")).toBe("button");
  expect(polygons[0].getAttribute("tabindex")).toBe("0");
  expect(polygons[1].getAttribute("tabindex")).toBe("-1");
  await act(async () =>
    polygons[0].dispatchEvent(new MouseEvent("mouseenter", { bubbles: true })),
  );
  expect(invoke).not.toHaveBeenCalledWith(
    "show_translation_popup",
    expect.anything(),
  );
  await act(async () => onFocus?.({ payload: { regionId: null } }));
  expect(focusFirst).toHaveBeenCalledOnce();
  const navigator = container.querySelector<HTMLElement>(".ocr-overlay")!;
  expect(document.activeElement).toBe(navigator);
  // A webview that cannot focus SVG must receive arrows through the HTML target.
  await act(async () =>
    navigator.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    ),
  );
  expect(polygons[1].getAttribute("aria-pressed")).toBe("true");
  await act(async () =>
    navigator.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }),
    ),
  );
  expect(polygons[0].getAttribute("aria-pressed")).toBe("true");
  await act(async () =>
    polygons[0].dispatchEvent(
      new KeyboardEvent("keydown", { key: "End", bubbles: true }),
    ),
  );
  expect(focusLast).toHaveBeenCalledTimes(2);
  expect(polygons[1].getAttribute("aria-pressed")).toBe("true");
  await act(async () =>
    navigator.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenCalledWith(
    "show_translation_popup",
    expect.objectContaining({ regionId: "1", text: "学校", keyboard: true }),
  );
  // Native popup dismissal requests the selected region, not the first one.
  await act(async () => onFocus?.({ payload: { regionId: "1" } }));
  expect(polygons[1].getAttribute("aria-pressed")).toBe("true");
  expect(document.activeElement).toBe(navigator);
  await act(async () =>
    navigator.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    ),
  );
  expect(polygons[0].getAttribute("aria-pressed")).toBe("true");
  await act(async () =>
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })),
  );
  expect(invoke).toHaveBeenCalledWith("hide_focused_overlay");
  await act(async () => root.unmount());
  expect(unlisten).toHaveBeenCalledOnce();
  root = createRoot(container);
  vi.mocked(listen).mockResolvedValue(vi.fn());
});

function translationOverlay(texts = ["今日はいい天気です", "学校へ行こう"]) {
  return {
    ...completedOverlay,
    regions: texts.map((text, index) => ({
      id: `bubble-${index}`,
      text,
      polygon: [
        { x: 20 + index * 200, y: 40 },
        { x: 160 + index * 200, y: 40 },
        { x: 160 + index * 200, y: 320 },
        { x: 20 + index * 200, y: 320 },
      ],
      orientation: "vertical",
      confidence: 0,
      type: "other",
      tokens: [],
      needsReview: index === 0,
      reviewReason:
        index === 0 ? "Approximate region; verify Japanese" : undefined,
    })),
  };
}

async function mountTranslationOverlay(overlay = translationOverlay()) {
  // jsdom has no text layout; model the measured panel width for fitting.
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(
    function (this: HTMLElement) {
      return Number.parseFloat(this.style.width) || 70;
    },
  );
  vi.stubGlobal("innerWidth", 320);
  vi.stubGlobal("innerHeight", 272);
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_overlay_state") return overlay;
    if (command === "reveal_ocr_overlay") return overlay.layout;
    return undefined;
  });
  await act(async () => root.render(<OcrOverlay />));
}

function translatedResponse(
  source: string,
  translatedText = "Nice weather today.",
) {
  return new Response(
    JSON.stringify({
      sourceText: source,
      translatedText,
      provider: "test-local",
      cached: false,
    }),
  );
}

it("requires the saved preference, shows translated text at Retina bounds, preserves review and click behavior, and restores Japanese", async () => {
  const fetch = vi
    .fn()
    .mockImplementation(async (_url, options) =>
      translatedResponse(JSON.parse(options.body).text),
    );
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  expect(container.querySelector(".overlay-translation-toggle")).toBeNull();
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => setBubbleTranslationEnabled(true));
  expect(fetch).toHaveBeenCalledTimes(2);
  const panel = container.querySelector("foreignObject")!;
  expect(panel.getAttribute("x")).toBe("10");
  expect(panel.getAttribute("y")).toBe("20");
  expect(panel.getAttribute("width")).toBe("70");
  expect(panel.getAttribute("height")).toBe("140");
  expect(panel.textContent).toBe("Nice weather today.");
  const polygon = container.querySelector("polygon.translated.needs-review")!;
  expect(polygon.getAttribute("aria-label")).toContain("Nice weather today.");
  expect(polygon.getAttribute("aria-label")).toContain("今日はいい天気です");
  expect(polygon.getAttribute("aria-label")).toContain("verify Japanese");
  expect(polygon.querySelector("title")).toBeNull();
  expect(container.querySelector(".bubble-translation-text[title]")).toBeNull();
  expect(container.querySelector(".overlay-translation-controls")).toBeNull();
  await act(async () =>
    container
      .querySelector(".bubble-translation-text")!
      .dispatchEvent(new MouseEvent("click", { bubbles: true })),
  );
  expect(invoke).toHaveBeenCalledWith(
    "show_translation_popup",
    expect.objectContaining({
      text: "今日はいい天気です",
      regionId: "bubble-0",
      translateOnOpen: true,
    }),
  );
  await act(async () => setBubbleTranslationEnabled(false));
  expect(container.querySelector("foreignObject")).toBeNull();
  expect(container.querySelector("polygon.translated")).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("deduplicates identical text, skips known sound effects/blank text, and reports every text panel for native clipping", async () => {
  const overlay = translationOverlay(["学校", "学校", "ドン", " "]);
  overlay.regions[2].type = "soundEffect";
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    x: 10,
    y: 20,
    width: 70,
    height: 140,
  } as DOMRect);
  const fetch = vi.fn().mockResolvedValue(translatedResponse("学校", "School"));
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay(overlay);
  await act(async () => setBubbleTranslationEnabled(true));
  expect(fetch).toHaveBeenCalledOnce();
  expect(container.querySelectorAll("foreignObject")).toHaveLength(2);
  const reports = vi
    .mocked(invoke)
    .mock.calls.filter(([command]) => command === "update_overlay_controls");
  expect(reports.at(-1)?.[1]).toMatchObject({
    rectangles: Array.from({ length: 3 }, () => ({
      x: 10,
      y: 20,
      width: 70,
      height: 140,
    })),
  });
});

it("stops on failure, keeps Japanese visible, and retries through the current provider", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        detail: "Select a local translation model in Settings.",
      }),
      { status: 409 },
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  await act(async () => setBubbleTranslationEnabled(true));
  expect(fetch).toHaveBeenCalledOnce();
  expect(container.querySelector("foreignObject")).toBeNull();
  expect(container.querySelector('[role="alert"]')?.textContent).toContain(
    "Select a local translation model",
  );
  fetch.mockImplementation(async (_url, options) =>
    translatedResponse(JSON.parse(options.body).text),
  );
  await act(async () =>
    Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Retry")!
      .click(),
  );
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(container.querySelectorAll("foreignObject")).toHaveLength(2);
});

it("aborts pending work when the setting is disabled and ignores late results instead of translating the next region", async () => {
  let finish!: (value: Response) => void;
  const fetch = vi.fn().mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  await act(async () => setBubbleTranslationEnabled(true));
  const signal = fetch.mock.calls[0][1].signal as AbortSignal;
  await act(async () => setBubbleTranslationEnabled(false));
  expect(signal.aborted).toBe(true);
  await act(async () => finish(translatedResponse("今日はいい天気です")));
  expect(fetch).toHaveBeenCalledOnce();
  expect(container.querySelector("foreignObject")).toBeNull();
});

it("cancels translations on native hide/scan replacement and removes its listener", async () => {
  let stop!: () => void;
  const unlisten = vi.fn();
  vi.mocked(listen).mockImplementation(async (name, callback) => {
    if (name === "stop-bubble-translations") {
      stop = callback as typeof stop;
      return unlisten;
    }
    return () => {};
  });
  const fetch = vi.fn().mockImplementation(() => new Promise(() => {}));
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  await act(async () => setBubbleTranslationEnabled(true));
  await act(async () => stop());
  expect(window.localStorage.getItem(bubbleTranslationPreferenceKey)).toBe(
    "true",
  );
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  await act(async () => root.unmount());
  expect(unlisten).toHaveBeenCalledOnce();
  root = createRoot(container);
  vi.mocked(listen).mockResolvedValue(vi.fn());
});

it("re-enabling asks the service again so a changed provider cannot reuse stale UI translations", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(translatedResponse("学校", "School"))
    .mockResolvedValueOnce(translatedResponse("学校", "The school"));
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay(translationOverlay(["学校"]));
  await act(async () => setBubbleTranslationEnabled(true));
  await act(async () => setBubbleTranslationEnabled(false));
  await act(async () => setBubbleTranslationEnabled(true));
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(container.querySelector("foreignObject")?.textContent).toBe(
    "The school",
  );
});

it.each(["demo", "manga"])(
  "never offers translation for %s demo or sound-effect-only results",
  async (engine) => {
    const overlay = translationOverlay(["ドン"]);
    overlay.engine = engine;
    overlay.regions[0].type = engine === "demo" ? "other" : "soundEffect";
    setBubbleTranslationEnabled(true);
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await mountTranslationOverlay(overlay);
    expect(container.querySelector(".overlay-translation-controls")).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  },
);

it("uses explicit demo labels and Space activation without inventing recognized text", async () => {
  const metadata = {
    displayId: "demo",
    displayName: "Demo",
    screenPhysicalBounds: { x: 0, y: 0, width: 100, height: 100 },
    selectionPhysicalBounds: { x: 0, y: 0, width: 100, height: 100 },
    selectionLogicalBounds: { x: 0, y: 0, width: 100, height: 100 },
    imageWidth: 100,
    imageHeight: 100,
    scaleFactor: 1,
  };
  vi.mocked(invoke).mockResolvedValue({
    metadata,
    regions: [
      {
        id: "demo",
        text: "Placeholder",
        polygon: [
          { x: 0, y: 0 },
          { x: 100, y: 0 },
          { x: 100, y: 100 },
        ],
        orientation: "horizontal",
        confidence: 0,
        type: "other",
        tokens: [],
      },
    ],
    engine: "demo",
    layout: {
      windowWidth: 100,
      windowHeight: 100,
      contentLeft: 0,
      contentTop: 0,
      contentWidth: 100,
      contentHeight: 100,
      toolbarTop: 0,
      toolbarHeight: 32,
    },
  });
  await act(async () => root.render(<OcrOverlay />));
  const polygon = container.querySelector("polygon.ocr-region")!;
  expect(polygon.getAttribute("aria-label")).toContain(
    "Demo boundary — no recognized text",
  );
  expect(polygon.getAttribute("aria-label")).not.toContain("Placeholder");
  await act(async () =>
    polygon.dispatchEvent(
      new KeyboardEvent("keydown", { key: " ", bubbles: true }),
    ),
  );
  expect(invoke).toHaveBeenCalledWith(
    "show_translation_popup",
    expect.objectContaining({ keyboard: true }),
  );
});

it("automatically translates every fresh or restored overlay with the persisted preference", async () => {
  setBubbleTranslationEnabled(true);
  const fetch = vi
    .fn()
    .mockImplementation(async (_url, options) =>
      translatedResponse(JSON.parse(options.body).text),
    );
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(container.querySelectorAll("foreignObject")).toHaveLength(2);
  await act(async () => root.unmount());
  root = createRoot(container);
  await mountTranslationOverlay();
  expect(fetch).toHaveBeenCalledTimes(4);
  expect(container.querySelectorAll("foreignObject")).toHaveLength(2);
  expect(window.localStorage.getItem(bubbleTranslationPreferenceKey)).toBe(
    "true",
  );
});

it("waits for the completed overlay to be revealed and follows setting changes from another window", async () => {
  setBubbleTranslationEnabled(true);
  let reveal!: (value: typeof completedOverlay.layout) => void;
  const fetch = vi
    .fn()
    .mockImplementation(async (_url, options) =>
      translatedResponse(JSON.parse(options.body).text),
    );
  vi.stubGlobal("fetch", fetch);
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "get_overlay_state") return translationOverlay();
    if (command === "reveal_ocr_overlay")
      return new Promise((resolve) => {
        reveal = resolve;
      });
    return undefined;
  });
  await act(async () => root.render(<OcrOverlay />));
  expect(fetch).not.toHaveBeenCalled();
  await act(async () => reveal(completedOverlay.layout));
  expect(fetch).toHaveBeenCalledTimes(2);
  await act(async () => {
    window.localStorage.setItem(bubbleTranslationPreferenceKey, "false");
    window.dispatchEvent(
      new StorageEvent("storage", { key: bubbleTranslationPreferenceKey }),
    );
  });
  expect(container.querySelector("foreignObject")).toBeNull();
  expect(container.querySelector(".overlay-translation-controls")).toBeNull();
});

it("updates visible translation size without translating again or changing automatic mode", async () => {
  setBubbleTranslationEnabled(true);
  setBubbleTranslationFontSize("24");
  const fetch = vi
    .fn()
    .mockImplementation(async (_url, options) =>
      translatedResponse(JSON.parse(options.body).text),
    );
  vi.stubGlobal("fetch", fetch);
  await mountTranslationOverlay();
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(
    container.querySelector("foreignObject span")?.getAttribute("style"),
  ).toContain("24px");
  await act(async () => setBubbleTranslationFontSize("32"));
  expect(
    container.querySelector("foreignObject span")?.getAttribute("style"),
  ).toContain("32px");
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(window.localStorage.getItem(bubbleTranslationPreferenceKey)).toBe(
    "true",
  );
});
