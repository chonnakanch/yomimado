export interface Point {
  x: number;
  y: number;
}

export interface TextToken {
  surface: string;
  reading: string;
  dictionaryForm: string;
  start: number;
  end: number;
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
}

export interface OcrDebugDetection {
  id: string;
  box: Point[];
  cropDataUrl?: string;
  text: string;
  status: "recognized" | "empty" | "invalid";
}

export interface OcrDebug {
  detections: OcrDebugDetection[];
  selectionText?: string;
  selectionFallbackUsed: boolean;
}

export interface OcrResponse {
  regions: TextRegion[];
  engine: "demo" | "manga";
  debug?: OcrDebug;
}
