import type {
  OcrDebug,
  OcrDebugDetection,
  OcrResponse,
  TextRegion,
} from "./ocr-types";
import { parseTextTokens } from "./token-validation";

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isPolygon(value: unknown, minimumPoints: number): boolean {
  return (
    Array.isArray(value) &&
    value.length >= minimumPoints &&
    value.every(
      (point: unknown) =>
        isRecord(point) && isFiniteNumber(point.x) && isFiniteNumber(point.y),
    )
  );
}

function isOptionalString(value: unknown): boolean {
  return value === undefined || typeof value === "string";
}

function isRetryCount(value: unknown): boolean {
  return (
    value === undefined ||
    (typeof value === "number" && Number.isSafeInteger(value) && value >= 0)
  );
}

function isRegion(value: unknown): value is TextRegion {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    !value.id ||
    typeof value.text !== "string" ||
    !isPolygon(value.polygon, 3) ||
    (value.orientation !== "horizontal" && value.orientation !== "vertical") ||
    !isFiniteNumber(value.confidence) ||
    value.confidence < 0 ||
    value.confidence > 1 ||
    !["dialogue", "narration", "soundEffect", "other"].includes(
      value.type as string,
    ) ||
    (value.geometrySource !== undefined &&
      value.geometrySource !== "selection" &&
      value.geometrySource !== "expandedCrop") ||
    (value.needsReview !== undefined &&
      typeof value.needsReview !== "boolean") ||
    !isOptionalString(value.reviewReason)
  ) {
    return false;
  }
  try {
    parseTextTokens(value.tokens, value.text);
    return true;
  } catch {
    return false;
  }
}

function isDebugDetection(value: unknown): value is OcrDebugDetection {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    isPolygon(value.box, 4) &&
    typeof value.text === "string" &&
    ["recognized", "empty", "invalid", "filtered"].includes(
      value.status as string,
    ) &&
    isOptionalString(value.cropDataUrl) &&
    isOptionalString(value.filterReason) &&
    isOptionalString(value.decisionReason) &&
    (value.detectionPass === undefined ||
      ["full", "tile", "mask"].includes(value.detectionPass as string))
  );
}

function isDebug(value: unknown): value is OcrDebug | undefined {
  return (
    value === undefined ||
    (isRecord(value) &&
      Array.isArray(value.detections) &&
      value.detections.every(isDebugDetection) &&
      isRetryCount(value.tileRetryCount) &&
      isRetryCount(value.maskRetryCount) &&
      isOptionalString(value.selectionText) &&
      typeof value.selectionFallbackUsed === "boolean")
  );
}

/** Validate the service boundary before geometry reaches capture/overlay code. */
export function parseOcrResponse(value: unknown): OcrResponse {
  if (
    !isRecord(value) ||
    (value.engine !== "demo" && value.engine !== "manga") ||
    !Array.isArray(value.regions) ||
    !value.regions.every(isRegion) ||
    new Set(value.regions.map((region) => region.id)).size !==
      value.regions.length ||
    !isDebug(value.debug)
  ) {
    throw new Error("OCR service returned invalid data");
  }
  return {
    regions: value.regions,
    engine: value.engine,
    ...(value.debug !== undefined ? { debug: value.debug } : {}),
  };
}
