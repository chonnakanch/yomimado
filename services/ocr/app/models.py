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


class OcrResponse(BaseModel):
    regions: list[TextRegion]
    engine: Literal["demo", "manga"]


class ErrorResponse(BaseModel):
    detail: str
