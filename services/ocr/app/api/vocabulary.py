import sqlite3

from fastapi import APIRouter, HTTPException

from app.models import SavedWord, SavedWordsResponse, SaveWordRequest
from app.vocabulary import VocabularyStore, default_vocabulary_path

router = APIRouter()
store = VocabularyStore(default_vocabulary_path())


@router.post("/api/v1/vocabulary", response_model=SavedWord)
def save_word(request: SaveWordRequest) -> SavedWord:
    try:
        return store.save(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/api/v1/vocabulary", response_model=SavedWordsResponse)
def list_words() -> SavedWordsResponse:
    try:
        return SavedWordsResponse(words=store.list())
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.delete("/api/v1/vocabulary/{word_id}", status_code=204)
def delete_word(word_id: int) -> None:
    if word_id < 1:
        raise HTTPException(status_code=422, detail="Invalid saved word ID")
    try:
        deleted = store.delete(word_id)
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved word not found")
