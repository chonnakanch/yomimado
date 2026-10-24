import { expect, it } from "vitest";
import {
  availableTranslationBounds,
  anchorTranslationBounds,
} from "./translation-layout";

it("allows width and height growth while staying inside capture edges", () => {
  for (const x of [0, 180]) {
    const source = { x, y: 40, width: 20, height: 80 };
    const expanded = availableTranslationBounds(source, [source], 200, 200);
    expect(expanded).toEqual({ x: 0, y: 0, width: 200, height: 200 });
    expect(anchorTranslationBounds(source, expanded, 100, 100).width).toBe(100);
  }
});

it("keeps all expanded pairs apart, including diagonal and stacked neighbours", () => {
  const regions = [
    { x: 10, y: 10, width: 60, height: 100 },
    { x: 90, y: 30, width: 50, height: 100 },
    { x: 20, y: 160, width: 60, height: 50 },
    { x: 180, y: 200, width: 40, height: 60 },
  ];
  const expanded = regions.map((source) =>
    availableTranslationBounds(source, regions, 400, 400),
  );
  for (let i = 0; i < expanded.length; i++)
    for (let j = i + 1; j < expanded.length; j++) {
      const a = expanded[i],
        b = expanded[j];
      expect(
        a.x + a.width <= b.x ||
          b.x + b.width <= a.x ||
          a.y + a.height <= b.y ||
          b.y + b.height <= a.y,
      ).toBe(true);
    }
  expect(expanded[0].width).toBeGreaterThan(regions[0].width);
  expect(expanded[0].height).toBeGreaterThan(regions[0].height);
});

it("preserves overlapping regions and never crops a large source", () => {
  const source = { x: 10, y: 10, width: 50, height: 100 };
  expect(
    availableTranslationBounds(
      source,
      [source, { ...source, x: 30 }],
      400,
      400,
    ),
  ).toBe(source);
  const wide = { ...source, width: 300, height: 250 };
  expect(availableTranslationBounds(wide, [wide], 400, 400)).toEqual(wide);
});

it("anchors short text at its source instead of filling all available space", () => {
  const source = { x: 80, y: 60, width: 50, height: 60 };
  const available = availableTranslationBounds(source, [source], 400, 400);
  expect(anchorTranslationBounds(source, available, 50, 60)).toEqual(source);
  const grown = anchorTranslationBounds(source, available, 150, 140);
  expect(grown).toEqual({ x: 30, y: 20, width: 150, height: 140 });
});
