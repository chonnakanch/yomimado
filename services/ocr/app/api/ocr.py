from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.models import OcrResponse
from app.pipeline.pipeline import OcrInput, OcrPipeline

router = APIRouter()
pipeline = OcrPipeline()


@router.post("/api/v1/ocr", response_model=OcrResponse, response_model_exclude_none=True)
async def ocr(image: UploadFile = File(...), debug: bool = Form(False)) -> OcrResponse:
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file")
    try:
        return await run_in_threadpool(
            pipeline.recognize,
            OcrInput(image_bytes=await image.read(), content_type=image.content_type, debug=debug),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (ImportError, FileNotFoundError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
