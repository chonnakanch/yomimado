// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CaptureDebugView } from "./CaptureDebugView";

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
      imagePath="/tmp/capture.png"
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
          },
        ],
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
    "10,20 90,20 90,220 10,220",
  );
  expect(container.textContent).toContain("数か月前");
  expect(container.textContent).toContain("confidence: unknown");
});

it("keeps the captured image visible when OCR fails", () => {
  const markup = renderToStaticMarkup(
    <CaptureDebugView
      imageDataUrl="data:image/png;base64,dGVzdA=="
      imagePath="/tmp/capture.png"
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
