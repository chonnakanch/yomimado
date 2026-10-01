// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CaptureDebugView, fitCaptureDebugImage } from "./CaptureDebugView";

it("fits tall and wide captures inside the debug preview without changing aspect ratio", () => {
  expect(fitCaptureDebugImage(1000, 2000, 900, 600)).toEqual({
    width: 300,
    height: 600,
  });
  expect(fitCaptureDebugImage(2000, 1000, 900, 600)).toEqual({
    width: 900,
    height: 450,
  });
  expect(fitCaptureDebugImage(240, 360, 900, 600)).toEqual({
    width: 240,
    height: 360,
  });
});

const metadata = {
  displayId: "test",
  displayName: "Test display",
  screenPhysicalBounds: { x: 0, y: 0, width: 1920, height: 1080 },
  selectionPhysicalBounds: { x: 100, y: 200, width: 240, height: 360 },
  selectionLogicalBounds: { x: 50, y: 100, width: 120, height: 180 },
  imageWidth: 240,
  imageHeight: 360,
  scaleFactor: 2,
};

it("shows the exact captured image and OCR text with image-space polygons", () => {
  const markup = renderToStaticMarkup(
    <CaptureDebugView
      imageDataUrl="data:image/png;base64,dGVzdA=="
      metadata={metadata}
      response={{
        engine: "manga",
        regions: [
          {
            id: "region-1",
            text: "数か月前",
            polygon: [
              { x: 10, y: 20 },
              { x: 90, y: 20 },
              { x: 90, y: 220 },
              { x: 10, y: 220 },
            ],
            orientation: "vertical",
            confidence: 0,
            type: "other",
            tokens: [],
            geometrySource: "selection",
          },
          {
            id: "region-2",
            text: "みて",
            polygon: [
              { x: 150, y: 30 },
              { x: 180, y: 30 },
              { x: 180, y: 90 },
              { x: 150, y: 90 },
            ],
            orientation: "vertical",
            confidence: 0,
            type: "other",
            tokens: [],
            needsReview: true,
            reviewReason:
              "Short Japanese-looking text from detector mask; verify on page",
          },
          {
            id: "region-3",
            text: "こっち",
            polygon: [
              { x: 100, y: 180 },
              { x: 130, y: 180 },
              { x: 130, y: 260 },
              { x: 100, y: 260 },
            ],
            orientation: "vertical",
            confidence: 0,
            type: "other",
            tokens: [],
            geometrySource: "expandedCrop",
            needsReview: true,
            reviewReason: "Expanded short vertical crop; area approximate",
          },
        ],
        debug: {
          tileRetryCount: 2,
          maskRetryCount: 2,
          detections: [
            {
              id: "detection-1",
              box: [
                { x: 12, y: 22 },
                { x: 80, y: 22 },
                { x: 80, y: 200 },
                { x: 12, y: 200 },
              ],
              cropDataUrl: "data:image/png;base64,Y3JvcA==",
              text: "数か月",
              status: "recognized",
            },
            {
              id: "detection-2",
              box: [
                { x: 100, y: 20 },
                { x: 140, y: 20 },
                { x: 140, y: 70 },
                { x: 100, y: 70 },
              ],
              text: "comipo Play",
              status: "filtered",
              filterReason: "No Japanese characters in the recognized text",
              detectionPass: "tile",
            },
            {
              id: "detection-3",
              box: [
                { x: 150, y: 30 },
                { x: 180, y: 30 },
                { x: 180, y: 90 },
                { x: 150, y: 90 },
              ],
              text: "みて",
              status: "recognized",
              detectionPass: "mask",
              decisionReason:
                "Short Japanese-looking text from detector mask; verify on page",
            },
          ],
          selectionText: "数か月前",
          selectionFallbackUsed: true,
        },
      }}
      error={null}
      onContinue={() => {}}
      onCancel={() => {}}
    />,
  );
  const container = document.createElement("div");
  container.innerHTML = markup;

  expect(container.querySelector("img")?.getAttribute("src")).toBe(
    "data:image/png;base64,dGVzdA==",
  );
  expect(container.querySelector("svg")?.getAttribute("viewBox")).toBe(
    "0 0 240 360",
  );
  expect(container.querySelector("polygon")?.getAttribute("points")).toBe(
    "12,22 80,22 80,200 12,200",
  );
  expect(
    container
      .querySelector(".capture-debug-final-region")
      ?.getAttribute("points"),
  ).toBe("10,20 90,20 90,220 10,220");
  expect(
    container.querySelector(".capture-debug-crop")?.getAttribute("src"),
  ).toBe("data:image/png;base64,Y3JvcA==");
  expect(container.textContent).toContain("数か月前");
  expect(container.textContent).toContain("confidence: unknown");
  expect(container.textContent).toContain("approximate selected-area box");
  expect(container.textContent).toContain("approximate expanded-crop box");
  expect(container.textContent).toContain("review suggested");
  expect(
    container.querySelector(".capture-debug-final-region.needs-review title")
      ?.textContent,
  ).toContain("verify on page");
  expect(container.textContent).toContain("Whole-selection retry");
  expect(container.textContent).toContain("tile retry");
  expect(container.textContent).toContain("Tile retry: 2 overlapping crop(s)");
  expect(container.textContent).toContain(
    "Text-mask retry: up to 2 tile(s) checked",
  );
  expect(container.textContent).toContain(
    "text-mask retry · recognized · みて",
  );
  expect(container.textContent).toContain(
    "Kept: Short Japanese-looking text from detector mask",
  );
  expect(
    container.querySelector(".capture-debug-detector-box.filtered title")
      ?.textContent,
  ).toContain("No Japanese characters");
  expect(container.textContent).toContain(
    "Filtered: No Japanese characters in the recognized text",
  );
  expect(container.textContent).toContain("no PNG saved to disk");
});

it("keeps the captured image visible when OCR fails", () => {
  const markup = renderToStaticMarkup(
    <CaptureDebugView
      imageDataUrl="data:image/png;base64,dGVzdA=="
      metadata={metadata}
      response={null}
      error="OCR service unavailable"
      onContinue={() => {}}
      onCancel={() => {}}
    />,
  );
  const container = document.createElement("div");
  container.innerHTML = markup;

  expect(container.querySelector("img")).not.toBeNull();
  expect(container.textContent).toContain("OCR service unavailable");
  expect(
    container.querySelector<HTMLButtonElement>(".capture-debug-actions button")
      ?.disabled,
  ).toBe(true);
});
