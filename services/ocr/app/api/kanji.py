from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, HTTPException

from app.dictionary.kanjidic import lookup
from app.models import KanjiEntry, KanjiRequest

router = APIRouter()


@router.post("/api/v1/kanji", response_model=KanjiEntry)
def kanji(request: KanjiRequest) -> KanjiEntry:
    try:
        entry = lookup(request.character)
    except (OSError, ValueError, ParseError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if entry is None:
        raise HTTPException(status_code=404, detail="Kanji not found in local KANJIDIC2")
    return entry
