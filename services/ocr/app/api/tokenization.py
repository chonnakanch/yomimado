from fastapi import APIRouter, HTTPException

from app.models import TokenizationRequest, TokenizationResponse
from app.tokenizer.sudachi import SudachiTokenizer

router = APIRouter()
tokenizer = SudachiTokenizer()


@router.post("/api/v1/tokenize", response_model=TokenizationResponse)
def tokenize(request: TokenizationRequest) -> TokenizationResponse:
    try:
        return TokenizationResponse(
            sourceText=request.text, tokens=tokenizer.tokenize(request.text)
        )
    except (RuntimeError, ImportError, OSError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
