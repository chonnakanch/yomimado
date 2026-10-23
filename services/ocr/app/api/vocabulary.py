import sqlite3

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from app.backup import MAX_BACKUP_BYTES, RestoreSummary, parse_backup
from app.models import (
    SavedSentence,
    SavedSentencesResponse,
    SavedWord,
    SavedWordsResponse,
    SaveSentenceRequest,
    SaveWordRequest,
)
from app.vocabulary import VocabularyStore, default_vocabulary_path

router = APIRouter()
store = VocabularyStore(default_vocabulary_path())


@router.get("/api/v1/backup")
def export_backup() -> Response:
    try:
        content = store.backup().model_dump_json().encode("utf-8")
        if len(content) > MAX_BACKUP_BYTES:
            raise ValueError("Saved data exceeds the 16 MiB backup size limit")
        return Response(content, media_type="application/json")
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="Saved data exceeds backup limits or has invalid records"
        ) from error
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(
            status_code=503, detail="Could not read saved data for backup"
        ) from error


@router.post("/api/v1/backup/preview", response_model=RestoreSummary)
@router.post("/api/v1/backup/restore", response_model=RestoreSummary)
async def restore_backup(request: Request) -> RestoreSummary:
    try:
        backup = await run_in_threadpool(parse_backup, await request.body())
        return await run_in_threadpool(
            store.restore, backup, preview=request.url.path.endswith("/preview")
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(
            status_code=503, detail="Could not restore saved data; no entries were added"
        ) from error


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


@router.post("/api/v1/sentences", response_model=SavedSentence)
def save_sentence(request: SaveSentenceRequest) -> SavedSentence:
    try:
        return store.save_sentence(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/api/v1/sentences", response_model=SavedSentencesResponse)
def list_sentences() -> SavedSentencesResponse:
    try:
        return SavedSentencesResponse(sentences=store.list_sentences())
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.delete("/api/v1/sentences/{sentence_id}", status_code=204)
def delete_sentence(sentence_id: int) -> None:
    if sentence_id < 1:
        raise HTTPException(status_code=422, detail="Invalid saved sentence ID")
    try:
        deleted = store.delete_sentence(sentence_id)
    except (OSError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved sentence not found")
