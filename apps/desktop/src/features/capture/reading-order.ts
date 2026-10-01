import type { TextRegion } from "../../lib/ocr-types";

interface PositionedRegion {
  region: TextRegion;
  originalIndex: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

function horizontalOverlap(a: PositionedRegion, b: PositionedRegion): number {
  const overlap = Math.min(a.right, b.right) - Math.max(a.left, b.left);
  const narrowerWidth = Math.min(a.right - a.left, b.right - b.left);
  return narrowerWidth > 0 ? overlap / narrowerWidth : 0;
}

export function orderMangaRegions(regions: TextRegion[]): TextRegion[] {
  const positioned: PositionedRegion[] = [];
  const unpositioned: TextRegion[] = [];
  regions.forEach((region, originalIndex) => {
    const xs = region.polygon.map((point) => point.x);
    const ys = region.polygon.map((point) => point.y);
    if (
      !xs.length ||
      !ys.length ||
      !xs.every(Number.isFinite) ||
      !ys.every(Number.isFinite)
    ) {
      unpositioned.push(region);
      return;
    }
    positioned.push({
      region,
      originalIndex,
      left: Math.min(...xs),
      right: Math.max(...xs),
      top: Math.min(...ys),
      bottom: Math.max(...ys),
    });
  });

  positioned.sort((a, b) => a.top - b.top || a.originalIndex - b.originalIndex);
  const bands: { bottom: number; regions: PositionedRegion[] }[] = [];
  for (const item of positioned) {
    const band = bands[bands.length - 1];
    if (band && item.top <= band.bottom) {
      band.bottom = Math.max(band.bottom, item.bottom);
      band.regions.push(item);
    } else {
      bands.push({ bottom: item.bottom, regions: [item] });
    }
  }

  const ordered: TextRegion[] = [];
  for (const band of bands) {
    const columns: PositionedRegion[][] = [];
    for (const item of band.regions.sort(
      (a, b) => b.right - a.right || a.originalIndex - b.originalIndex,
    )) {
      const column = columns.find(
        (candidate) => horizontalOverlap(candidate[0], item) > 0.5,
      );
      if (column) column.push(item);
      else columns.push([item]);
    }
    for (const column of columns) {
      column.sort((a, b) => a.top - b.top || a.originalIndex - b.originalIndex);
      ordered.push(...column.map((item) => item.region));
    }
  }
  return [...ordered, ...unpositioned];
}
