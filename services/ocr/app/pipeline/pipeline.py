from __future__ import annotations

import struct
from dataclasses import dataclass
from os import environ

from app.models import OcrResponse, Point, TextRegion


@dataclass(frozen=True)
class OcrInput:
    image_bytes: bytes
    content_type: str | None


def _parse_png_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    if len(image_bytes) >= 24 and image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", image_bytes[16:24])
        return w, h
    return None


class OcrPipeline:
    """Choose a local model pipeline when its paths are configured.

    The unconfigured service returns a demo boundary, not a claimed OCR result.
    """

    @property
    def engine(self) -> str:
        return "manga" if environ.get("YOMIMADO_DETECTOR_REPO") else "demo"

    def recognize(self, input_image: OcrInput) -> OcrResponse:
        if not input_image.image_bytes:
            raise ValueError("The uploaded image is empty")

        dimensions = _parse_png_dimensions(input_image.image_bytes)
        if not dimensions or dimensions[0] <= 0 or dimensions[1] <= 0:
            raise ValueError("Upload a valid PNG capture")

        if self.engine == "manga":
            from app.pipeline.real_ocr import recognize_with_models

            return recognize_with_models(input_image.image_bytes)

        width, height = map(float, dimensions)

        placeholder_region = TextRegion(
            id="selection-boundary-demo",
            text="Demo: selected area, not recognized text",
            polygon=[
                Point(x=0, y=0),
                Point(x=width, y=0),
                Point(x=width, y=height),
                Point(x=0, y=height),
            ],
            orientation="horizontal",
            confidence=0,
            type="other",
            tokens=[],
        )

        return OcrResponse(regions=[placeholder_region], engine="demo")
