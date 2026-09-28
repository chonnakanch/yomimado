// @vitest-environment jsdom
import { beforeEach, expect, it } from "vitest";
import {
  loadScanArea,
  physicalToSelection,
  saveScanArea,
  selectionToPhysical,
  type CaptureSurface,
} from "./scan-area";

const surface: CaptureSurface = {
  displayId: "Retina",
  screenPhysicalBounds: { x: -2940, y: 0, width: 2940, height: 1912 },
  selectorPhysicalBounds: { x: -2940, y: 66, width: 2940, height: 1912 },
  scaleFactor: 2,
};

beforeEach(() => window.localStorage.clear());

it("round-trips a scan area through physical and selector coordinates", () => {
  const viewport = { width: 1470, height: 956 };
  const selection = { x: 100, y: 100, width: 900, height: 600 };
  const physical = selectionToPhysical(selection, viewport, surface);
  expect(physical).toEqual({ x: -2740, y: 266, width: 1800, height: 1200 });
  saveScanArea(surface, physical!);
  expect(
    physicalToSelection(loadScanArea(surface)!, viewport, surface),
  ).toEqual(selection);
});

it("does not reuse an area after display resolution changes", () => {
  saveScanArea(surface, { x: -2700, y: 200, width: 1200, height: 900 });
  expect(
    loadScanArea({
      ...surface,
      screenPhysicalBounds: { ...surface.screenPhysicalBounds, width: 3000 },
    }),
  ).toBeNull();
});

it("keeps the physical area fixed if the selector window shifts", () => {
  const area = { x: -2700, y: 266, width: 1200, height: 900 };
  expect(
    physicalToSelection(
      area,
      { width: 1470, height: 956 },
      {
        ...surface,
        selectorPhysicalBounds: {
          ...surface.selectorPhysicalBounds,
          y: 86,
        },
      },
    ),
  ).toEqual({ x: 120, y: 90, width: 600, height: 450 });
});

it("rejects areas outside the visible display or selector", () => {
  const viewport = { width: 1470, height: 956 };
  expect(
    selectionToPhysical(
      { x: 100, y: 900, width: 100, height: 50 },
      viewport,
      surface,
    ),
  ).toBeNull();
  expect(
    physicalToSelection(
      { x: -2700, y: 20, width: 300, height: 300 },
      viewport,
      surface,
    ),
  ).toBeNull();
});
