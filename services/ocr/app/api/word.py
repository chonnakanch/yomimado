import sqlite3
from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, HTTPException

from app.dictionary.jmdict import lookup
from app.models import WordLookupRequest, WordLookupResponse

router = APIRouter()


@router.post("/api/v1/word", response_model=WordLookupResponse)
def word(request: WordLookupRequest) -> WordLookupResponse:
    try:
        entries = lookup(request.surface, request.dictionaryForm, request.reading)
    except (OSError, ValueError, ParseError, sqlite3.DatabaseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return WordLookupResponse(entries=entries)
