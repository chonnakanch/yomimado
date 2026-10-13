import { expect, it } from "vitest";
import { parseOcrResponse } from "./ocr-response";
import type { OcrResponse, TextRegion } from "./ocr-types";

const region: TextRegion = {
  id: "region-1",
  text: "🙂学校。",
  polygon: [
    { x: 0, y: 0 },
    { x: 80, y: 0 },
    { x: 80, y: 200 },
    { x: 0, y: 200 },
  ],
  orientation: "vertical",
  confidence: 0,
  type: "dialogue",
  tokens: [
    {
      surface: "学校",
      reading: "ガッコウ",
      dictionaryForm: "学校",
      start: 1,
      end: 3,
      partOfSpeech: "名詞",
    },
  ],
  geometrySource: "expandedCrop",
  needsReview: true,
  reviewReason: "Recognition confidence is unknown",
};

const response: OcrResponse = {
  regions: [region],
  engine: "manga",
  debug: {
    detections: [
      {
        id: "detection-1",
        box: region.polygon,
        text: region.text,
        status: "recognized",
        detectionPass: "tile",
        cropDataUrl: "data:image/png;base64,eA==",
      },
    ],
    tileRetryCount: 2,
    maskRetryCount: 0,
    selectionText: region.text,
    selectionFallbackUsed: false,
  },
};

it("preserves vertical geometry, unknown confidence, review metadata and code-point token offsets", () => {
  expect(parseOcrResponse(response)).toEqual(response);
});

it("accepts empty results and regions without optional metadata", () => {
  expect(parseOcrResponse({ regions: [], engine: "demo" })).toEqual({
    regions: [],
    engine: "demo",
  });
  const { geometrySource, needsReview, reviewReason, ...minimal } = region;
  expect(
    parseOcrResponse({ regions: [minimal], engine: "manga" }).regions,
  ).toEqual([minimal]);
});

it.each([
  null,
  [],
  { regions: null, engine: "manga" },
  { regions: [], engine: "cloud" },
  { regions: [region, region], engine: "manga" },
])(
  "rejects malformed response envelopes and duplicate region IDs: %j",
  (value) => {
    expect(() => parseOcrResponse(value)).toThrow(
      "OCR service returned invalid data",
    );
  },
);

it.each([
  { polygon: undefined },
  {
    polygon: [
      { x: 0, y: 0 },
      { x: 80, y: 0 },
    ],
  },
  {
    polygon: [
      { x: NaN, y: 0 },
      { x: 80, y: 0 },
      { x: 0, y: 200 },
    ],
  },
  {
    polygon: [
      { x: 0, y: Infinity },
      { x: 80, y: 0 },
      { x: 0, y: 200 },
    ],
  },
  { orientation: "diagonal" },
  { confidence: -1 },
  { confidence: 1.1 },
  { confidence: NaN },
  { type: "unknown" },
  { geometrySource: "guessed" },
  { needsReview: "yes" },
  { reviewReason: 42 },
  { tokens: [{ ...region.tokens[0], start: 2, end: 4 }] },
  { tokens: [region.tokens[0], region.tokens[0]] },
])("rejects invalid geometry, metadata and token offsets: %j", (patch) => {
  expect(() =>
    parseOcrResponse({ regions: [{ ...region, ...patch }], engine: "manga" }),
  ).toThrow("OCR service returned invalid data");
});

it.each([
  { detections: {} },
  { detections: [{ ...response.debug!.detections[0], box: [] }] },
  { detections: [{ ...response.debug!.detections[0], status: "unknown" }] },
  {
    detections: [
      { ...response.debug!.detections[0], detectionPass: "unknown" },
    ],
  },
  { tileRetryCount: -1 },
  { maskRetryCount: 1.5 },
  { selectionText: 42 },
  { selectionFallbackUsed: "yes" },
])("rejects malformed capture diagnostics: %j", (patch) => {
  expect(() =>
    parseOcrResponse({ ...response, debug: { ...response.debug, ...patch } }),
  ).toThrow("OCR service returned invalid data");
});
