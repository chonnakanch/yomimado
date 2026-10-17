from fastapi import APIRouter, HTTPException

from app.models import TokenizationRequest, TokenizationResponse
from app.tokenizer.provider import get_tokenizer

router = APIRouter()


@router.post("/api/v1/tokenize", response_model=TokenizationResponse)
def tokenize(request: TokenizationRequest) -> TokenizationResponse:
    try:
        return TokenizationResponse(
            sourceText=request.text, tokens=get_tokenizer().tokenize(request.text)
        )
    except (RuntimeError, ImportError, OSError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
