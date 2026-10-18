import sqlite3
from os import environ

from fastapi import APIRouter, HTTPException

from app.models import TranslationRequest, TranslationResponse
from app.translation import TranslationService, default_cache_path
from app.translation_preferences import ConfiguredTranslationProvider
from app.translation_resources import local_model_path, resources

router = APIRouter()
service = TranslationService(ConfiguredTranslationProvider(), default_cache_path())


@router.get("/api/v1/translation-model")
def model_status():
    try:
        if environ.get("YOMIMADO_TRANSLATION_MODEL"):
            local_model_path()
            return {"state": "ready", "receivedBytes": 0, "downloadBytes": 0, "error": None}
        return resources().status()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/api/v1/translation-model/install")
def install_model():
    try:
        return resources().start()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/api/v1/translate", response_model=TranslationResponse)
def translate(request: TranslationRequest) -> TranslationResponse:
    try:
        return service.translate(request.text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, ImportError, RuntimeError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
