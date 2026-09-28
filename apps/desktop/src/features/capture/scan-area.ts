import type { Rectangle } from "../../lib/coordinates";

export interface CaptureSurface {
  displayId: string;
  screenPhysicalBounds: Rectangle;
  selectorPhysicalBounds: Rectangle;
  scaleFactor: number;
}

const storagePrefix = "yomimado.scan-area.v1.";

function finiteRectangle(rectangle: Rectangle): boolean {
  return [rectangle.x, rectangle.y, rectangle.width, rectangle.height].every(
    Number.isFinite,
  );
}

function contains(outer: Rectangle, inner: Rectangle): boolean {
  return (
    inner.x >= outer.x &&
    inner.y >= outer.y &&
    inner.x + inner.width <= outer.x + outer.width &&
    inner.y + inner.height <= outer.y + outer.height
  );
}

export function scanAreaKey(surface: CaptureSurface): string {
  const bounds = surface.screenPhysicalBounds;
  return `${storagePrefix}${JSON.stringify([
    surface.displayId,
    bounds.x,
    bounds.y,
    bounds.width,
    bounds.height,
    surface.scaleFactor,
  ])}`;
}

export function selectionToPhysical(
  selection: Rectangle,
  viewport: { width: number; height: number },
  surface: CaptureSurface,
): Rectangle | null {
  const selector = surface.selectorPhysicalBounds;
  if (
    !finiteRectangle(selection) ||
    !finiteRectangle(selector) ||
    viewport.width <= 0 ||
    viewport.height <= 0 ||
    selection.width < 4 ||
    selection.height < 4
  ) {
    return null;
  }
  const result = {
    x: selector.x + (selection.x * selector.width) / viewport.width,
    y: selector.y + (selection.y * selector.height) / viewport.height,
    width: (selection.width * selector.width) / viewport.width,
    height: (selection.height * selector.height) / viewport.height,
  };
  return contains(surface.screenPhysicalBounds, result) ? result : null;
}

export function physicalToSelection(
  area: Rectangle,
  viewport: { width: number; height: number },
  surface: CaptureSurface,
): Rectangle | null {
  const selector = surface.selectorPhysicalBounds;
  if (
    !finiteRectangle(area) ||
    !finiteRectangle(selector) ||
    area.width <= 0 ||
    area.height <= 0 ||
    selector.width <= 0 ||
    selector.height <= 0 ||
    viewport.width <= 0 ||
    viewport.height <= 0 ||
    !contains(surface.screenPhysicalBounds, area) ||
    !contains(selector, area)
  ) {
    return null;
  }
  return {
    x: ((area.x - selector.x) * viewport.width) / selector.width,
    y: ((area.y - selector.y) * viewport.height) / selector.height,
    width: (area.width * viewport.width) / selector.width,
    height: (area.height * viewport.height) / selector.height,
  };
}

export function loadScanArea(surface: CaptureSurface): Rectangle | null {
  const raw = window.localStorage.getItem(scanAreaKey(surface));
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null) return null;
    const area = value as Rectangle;
    return finiteRectangle(area) && area.width > 0 && area.height > 0
      ? area
      : null;
  } catch {
    return null;
  }
}

export function saveScanArea(surface: CaptureSurface, area: Rectangle): void {
  window.localStorage.setItem(scanAreaKey(surface), JSON.stringify(area));
}
