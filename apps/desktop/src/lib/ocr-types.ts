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
}

export interface OcrResponse {
  regions: TextRegion[];
  engine: "demo" | "manga";
}
