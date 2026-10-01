import { expect, it } from "vitest";
import type { TextRegion } from "../../lib/ocr-types";
import { orderMangaRegions } from "./reading-order";

function region(
  id: string,
  x: number,
  y: number,
  width = 40,
  height = 100,
): TextRegion {
  return {
    id,
    text: id,
    polygon: [
      { x, y },
      { x: x + width, y },
      { x: x + width, y: y + height },
      { x, y: y + height },
    ],
    orientation: "vertical",
    confidence: 0,
    type: "dialogue",
    tokens: [],
  };
}

it("reads upper bands before lower bands, and right columns before left columns", () => {
  const lowerRight = region("lower right", 800, 400);
  const upperLeft = region("upper left", 200, 110);
  const upperRight = region("upper right", 800, 100);

  expect(orderMangaRegions([lowerRight, upperLeft, upperRight])).toEqual([
    upperRight,
    upperLeft,
    lowerRight,
  ]);
});

it("reads top to bottom within an overlapping vertical column", () => {
  const lower = region("lower", 790, 180);
  const left = region("left", 600, 150);
  const upper = region("upper", 800, 100);

  expect(orderMangaRegions([lower, left, upper])).toEqual([upper, lower, left]);
});

it("preserves region data and leaves unusable geometry at the end", () => {
  const missing = { ...region("missing", 0, 0), polygon: [] };
  const right = region("right", 800, 100);
  const original = [missing, right];

  expect(orderMangaRegions(original)).toEqual([right, missing]);
  expect(original).toEqual([missing, right]);
});
