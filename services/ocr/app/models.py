from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class TextToken(BaseModel):
    surface: str
    reading: str
    dictionaryForm: str
    start: int
    end: int
    partOfSpeech: str


class TextRegion(BaseModel):
    id: str
    text: str
    polygon: list[Point] = Field(min_length=3)
    orientation: Literal["horizontal", "vertical"]
    confidence: float = Field(ge=0, le=1)
    type: Literal["dialogue", "narration", "soundEffect", "other"]
    tokens: list[TextToken]
    geometrySource: Literal["selection"] | None = None


class OcrDebugDetection(BaseModel):
    id: str
    box: list[Point] = Field(min_length=4)
    cropDataUrl: str | None = None
    text: str
    status: Literal["recognized", "empty", "invalid", "filtered"]
    filterReason: str | None = None
    detectionPass: Literal["full", "tile"] = "full"


class OcrDebug(BaseModel):
    detections: list[OcrDebugDetection]
    tileRetryCount: int = 0
    selectionText: str | None = None
    selectionFallbackUsed: bool = False


class OcrResponse(BaseModel):
    regions: list[TextRegion]
    engine: Literal["demo", "manga"]
    debug: OcrDebug | None = None


class ErrorResponse(BaseModel):
    detail: str


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TokenizationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TokenizationResponse(BaseModel):
    sourceText: str
    tokens: list[TextToken]


class KanjiRequest(BaseModel):
    character: str = Field(min_length=1, max_length=1)


class KanjiEntry(BaseModel):
    character: str
    onReadings: list[str]
    kunReadings: list[str]
    meanings: list[str]


class WordLookupRequest(BaseModel):
    surface: str = Field(min_length=1, max_length=100)
    dictionaryForm: str = Field(min_length=1, max_length=100)
    reading: str = Field(max_length=100)


class WordSense(BaseModel):
    glosses: list[str]


class WordEntry(BaseModel):
    expression: str
    reading: str
    senses: list[WordSense]
    match: Literal["surface", "dictionaryForm"]
    readingMatch: bool
    common: bool


class WordLookupResponse(BaseModel):
    entries: list[WordEntry]


class SaveWordRequest(BaseModel):
    surface: str = Field(min_length=1, max_length=100)
    reading: str = Field(max_length=100)
    dictionaryForm: str = Field(min_length=1, max_length=100)
    meanings: list[str] = Field(default_factory=list, max_length=100)
    sourceText: str = Field(min_length=1, max_length=2000)


class SavedWord(BaseModel):
    id: int
    surface: str
    reading: str
    dictionaryForm: str
    meanings: list[str]
    sourceText: str
    createdAt: str


class SavedWordsResponse(BaseModel):
    words: list[SavedWord]


class KanjiExamplesRequest(BaseModel):
    character: str = Field(min_length=1, max_length=1)
    excludeWord: str = Field(default="", max_length=100)


class KanjiExample(BaseModel):
    expression: str
    reading: str
    meanings: list[str]


class KanjiExamplesResponse(BaseModel):
    examples: list[KanjiExample]


class TranslationResponse(BaseModel):
    sourceText: str
    translatedText: str
    provider: str
    cached: bool
