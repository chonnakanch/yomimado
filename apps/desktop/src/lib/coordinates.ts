import type { Point } from "./ocr-types";

export interface Rectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Physical capture metadata supplied by the native capture layer. */
export interface CaptureMetadata {
  displayId: string;
  displayName: string;
  screenPhysicalBounds: Rectangle;
  selectionPhysicalBounds: Rectangle;
  selectionLogicalBounds: Rectangle;
  imageWidth: number;
  imageHeight: number;
  scaleFactor: number;
}

/** Normalize a drag in its original coordinate space. */
export function normalizeRectangle(start: Point, end: Point): Rectangle {
  return {
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y),
  };
}

/**
 * Convert OCR image coordinates to logical coordinates relative to the overlay window.
 * The overlay window is already positioned at selectionLogicalBounds on screen.
 */
export function ocrPointToOverlay(
  point: Point,
  capture: CaptureMetadata,
  viewport: { width: number; height: number } = capture.selectionLogicalBounds,
): Point {
  return {
    x: (point.x * viewport.width) / capture.imageWidth,
    y: (point.y * viewport.height) / capture.imageHeight,
  };
}

export function ocrPolygonToOverlay(
  points: Point[],
  capture: CaptureMetadata,
  viewport: { width: number; height: number } = capture.selectionLogicalBounds,
): Point[] {
  return points.map((point) => ocrPointToOverlay(point, capture, viewport));
}

/**
 * Convert OCR image coordinates to absolute screen logical coordinates.
 */
export function ocrPointToScreen(
  point: Point,
  capture: CaptureMetadata,
): Point {
  const overlayPoint = ocrPointToOverlay(point, capture);
  return {
    x: capture.selectionLogicalBounds.x + overlayPoint.x,
    y: capture.selectionLogicalBounds.y + overlayPoint.y,
  };
}

export function ocrPolygonToScreen(
  points: Point[],
  capture: CaptureMetadata,
): Point[] {
  return points.map((point) => ocrPointToScreen(point, capture));
}
