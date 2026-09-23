from fastapi import APIRouter

from app.pipeline.pipeline import OcrPipeline

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ocr": OcrPipeline().engine}
