from fastapi import APIRouter, Depends, HTTPException

from app.models import TokenizationRequest, TokenizationResponse
from app.tokenizer import JapaneseTokenizer
from app.tokenizer.provider import get_tokenizer

router = APIRouter()


def resolve_tokenizer() -> JapaneseTokenizer:
    """Wire the selected adapter at the API boundary, keeping failures explicit."""
    try:
        return get_tokenizer()
    except (RuntimeError, ImportError, OSError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/api/v1/tokenize", response_model=TokenizationResponse)
def tokenize(
    request: TokenizationRequest,
    tokenizer: JapaneseTokenizer = Depends(resolve_tokenizer),
) -> TokenizationResponse:
    try:
        return TokenizationResponse(
            sourceText=request.text, tokens=tokenizer.tokenize(request.text)
        )
    except (RuntimeError, ImportError, OSError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
