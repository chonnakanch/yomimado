from fastapi import APIRouter, HTTPException

from app.models import TranslationRequest, TranslationResponse
from app.translation import LocalMarianProvider, TranslationService, default_cache_path

router = APIRouter()
service = TranslationService(LocalMarianProvider(), default_cache_path())


@router.post("/api/v1/translate", response_model=TranslationResponse)
def translate(request: TranslationRequest) -> TranslationResponse:
    try:
        return service.translate(request.text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, ImportError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
