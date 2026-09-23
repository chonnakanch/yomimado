import { describe, expect, it } from "vitest";
import {
  normalizeRectangle,
  ocrPointToOverlay,
  ocrPointToScreen,
  type CaptureMetadata,
} from "./coordinates";

const capture = (scaleFactor: number): CaptureMetadata => ({
  displayId: "test",
  displayName: "Test display",
  screenPhysicalBounds: { x: -1920, y: 0, width: 3840, height: 2160 },
  selectionPhysicalBounds: {
    x: -1920 + 100 * scaleFactor,
    y: 200 * scaleFactor,
    width: 400 * scaleFactor,
    height: 200 * scaleFactor,
  },
  selectionLogicalBounds: { x: 100, y: 200, width: 400, height: 200 },
  imageWidth: 400 * scaleFactor,
  imageHeight: 200 * scaleFactor,
  scaleFactor,
});

describe("normalizeRectangle", () => {
  it("normalizes an up-left drag", () => {
    expect(normalizeRectangle({ x: 40, y: 60 }, { x: 10, y: 20 })).toEqual({
      x: 10,
      y: 20,
      width: 30,
      height: 40,
    });
  });

  it("normalizes a down-right drag unchanged", () => {
    expect(normalizeRectangle({ x: 10, y: 20 }, { x: 50, y: 80 })).toEqual({
      x: 10,
      y: 20,
      width: 40,
      height: 60,
    });
  });
});

describe("ocrPointToOverlay", () => {
  it("maps a 1x image coordinate into overlay window logical coordinates", () => {
    expect(ocrPointToOverlay({ x: 200, y: 100 }, capture(1))).toEqual({
      x: 200,
      y: 100,
    });
  });

  it("maps a 2x Retina image coordinate into overlay window logical coordinates", () => {
    expect(ocrPointToOverlay({ x: 400, y: 200 }, capture(2))).toEqual({
      x: 200,
      y: 100,
    });
  });

  it("maps Windows 125% and 150% capture pixels into the same logical point", () => {
    expect(ocrPointToOverlay({ x: 250, y: 125 }, capture(1.25))).toEqual({
      x: 200,
      y: 100,
    });
    expect(ocrPointToOverlay({ x: 300, y: 150 }, capture(1.5))).toEqual({
      x: 200,
      y: 100,
    });
  });

  it("keeps image origin at overlay window origin", () => {
    expect(ocrPointToOverlay({ x: 0, y: 0 }, capture(1.25))).toEqual({
      x: 0,
      y: 0,
    });
  });

  it("uses the actual overlay viewport when the window is rounded by the OS", () => {
    expect(
      ocrPointToOverlay({ x: 400, y: 200 }, capture(2), {
        width: 398,
        height: 201,
      }),
    ).toEqual({ x: 199, y: 100.5 });
  });
});

describe("ocrPointToScreen", () => {
  it("maps image coordinates to absolute screen logical coordinates including selection origin", () => {
    expect(ocrPointToScreen({ x: 200, y: 100 }, capture(1))).toEqual({
      x: 300,
      y: 300,
    });
    expect(ocrPointToScreen({ x: 400, y: 200 }, capture(2))).toEqual({
      x: 300,
      y: 300,
    });
    expect(ocrPointToScreen({ x: 0, y: 0 }, capture(1.25))).toEqual({
      x: 100,
      y: 200,
    });
  });
});
