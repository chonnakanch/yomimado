export interface Point {
  x: number;
  y: number;
}

export interface TextToken {
  surface: string;
  reading: string;
  dictionaryForm: string;
  start: number; // Unicode code-point offset in the original OCR string
  end: number; // Exclusive Unicode code-point offset
  partOfSpeech: string;
}

export type TextRegionType = "dialogue" | "narration" | "soundEffect" | "other";

export interface TextRegion {
  id: string;
  text: string;
  polygon: Point[];
  orientation: "horizontal" | "vertical";
  confidence: number;
  type: TextRegionType;
  tokens: TextToken[];
  geometrySource?: "selection";
  needsReview?: boolean;
  reviewReason?: string;
}

export interface OcrDebugDetection {
  id: string;
  box: Point[];
  cropDataUrl?: string;
  text: string;
  status: "recognized" | "empty" | "invalid" | "filtered";
  filterReason?: string;
  decisionReason?: string;
  detectionPass?: "full" | "tile" | "mask";
}

export interface OcrDebug {
  detections: OcrDebugDetection[];
  tileRetryCount?: number;
  maskRetryCount?: number;
  selectionText?: string;
  selectionFallbackUsed: boolean;
}

export interface OcrResponse {
  regions: TextRegion[];
  engine: "demo" | "manga";
  debug?: OcrDebug;
}
