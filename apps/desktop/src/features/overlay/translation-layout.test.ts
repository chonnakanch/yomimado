import { expect, it } from "vitest";
import { widenTranslationBounds } from "./translation-layout";

it("widens narrow text while keeping the panel inside the captured area", () => {
  for (const x of [0, 180]) {
    const source = { x, y: 40, width: 20, height: 80 };
    const expanded = widenTranslationBounds(source, [source], 200);
    expect(expanded.width).toBe(32);
    expect(expanded.x).toBeGreaterThanOrEqual(0);
    expect(expanded.x + expanded.width).toBeLessThanOrEqual(200);
    expect(expanded.y).toBe(source.y);
    expect(expanded.height).toBe(source.height);
  }
});

it("shares the gap between adjacent regions without overlapping their enlarged panels", () => {
  const left = { x: 10, y: 0, width: 60, height: 100 };
  const right = { x: 90, y: 20, width: 50, height: 100 };
  const neighbours = [left, right];
  const a = widenTranslationBounds(left, neighbours, 200);
  const b = widenTranslationBounds(right, neighbours, 200);
  expect(a.x + a.width + 4).toBeLessThanOrEqual(b.x);
  expect(a.width).toBeGreaterThan(left.width);
  expect(b.width).toBeGreaterThan(right.width);
});

it("leaves overlapping or already-wide regions unchanged", () => {
  const source = { x: 10, y: 10, width: 50, height: 100 };
  expect(
    widenTranslationBounds(source, [source, { ...source, x: 30 }], 400),
  ).toBe(source);
  const wide = { ...source, width: 200 };
  expect(widenTranslationBounds(wide, [wide], 400)).toEqual(wide);
});

it("allows horizontal room beside text on a separate row", () => {
  const source = { x: 50, y: 20, width: 50, height: 100 };
  const below = { x: 30, y: 120, width: 150, height: 100 };
  expect(widenTranslationBounds(source, [source, below], 200)).toEqual({
    x: 35,
    y: 20,
    width: 80,
    height: 100,
  });
});
