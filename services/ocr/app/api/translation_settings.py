"""Local-only translation selection, import and explicit Ollama model downloads."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import translation_preferences as preferences
from app.ollama_translation import downloads, installed_models

router = APIRouter()


class Selection(BaseModel):
    provider: Literal["builtin", "imported", "ollama"]
    model: str = Field(default="", max_length=200)


class ImportModel(BaseModel):
    folder: str = Field(min_length=1, max_length=4096)


class OllamaModel(BaseModel):
    model: str = Field(min_length=1, max_length=200)


def setup_call(action):
    try:
        return action()
    except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/api/v1/translation-settings")
def settings():
    return setup_call(preferences.settings_status)


@router.post("/api/v1/translation-settings")
def select(request: Selection):
    return setup_call(lambda: preferences.select_provider(request.provider, request.model))


@router.post("/api/v1/translation-settings/import")
def import_model(request: ImportModel):
    return setup_call(lambda: preferences.import_model(request.folder))


@router.get("/api/v1/translation-settings/ollama")
def ollama_status():
    try:
        return {"models": installed_models(), "error": None, "download": downloads.status()}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        return {"models": [], "error": str(error), "download": downloads.status()}


@router.post("/api/v1/translation-settings/ollama/pull")
def ollama_pull(request: OllamaModel):
    return setup_call(lambda: downloads.start(request.model))
