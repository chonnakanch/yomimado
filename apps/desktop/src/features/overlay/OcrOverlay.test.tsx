// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { OcrOverlay } from "./OcrOverlay";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
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
});

it("loads a text-heavy OCR result from native state instead of the URL", async () => {
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
  expect(reviewRegion?.querySelector("title")?.textContent).toContain(
    "verify on page",
  );
  expect(container.textContent).toContain("Dashed gold: check OCR text");
  expect(container.textContent).toContain("Approximate OCR area");
  expect(container.querySelector(".overlay-reading-order")).toBeNull();
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
});

it("steps through estimated scan order and opens the selected region", async () => {
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
    text,
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
  expect(
    container.querySelector(".overlay-reading-order")?.textContent,
  ).toContain("Est. 1/2 · right");
  expect(
    container.querySelector("polygon.ocr-region.active title")?.textContent,
  ).toContain("1. right");

  await act(async () => {
    container
      .querySelector<HTMLButtonElement>('button[aria-label="Next text region"]')
      ?.click();
  });
  expect(
    container.querySelector(".overlay-reading-order")?.textContent,
  ).toContain("Est. 2/2 · left");

  await act(async () => {
    container
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Open selected text region"]',
      )
      ?.click();
  });
  expect(invoke).toHaveBeenCalledWith(
    "show_translation_popup",
    expect.objectContaining({ text: "left" }),
  );
});
