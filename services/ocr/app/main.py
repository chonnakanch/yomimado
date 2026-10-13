from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.kanji import router as kanji_router
from app.api.ocr import router as ocr_router
from app.api.tokenization import router as tokenization_router
from app.api.translation import router as translation_router
from app.api.vocabulary import router as vocabulary_router
from app.api.word import router as word_router
from app.security import ALLOWED_ORIGINS, CLIENT_HEADER, LocalRequestMiddleware

app = FastAPI(title="YomiMado local OCR service", version="0.1.0")

app.add_middleware(LocalRequestMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", CLIENT_HEADER],
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"], www_redirect=False
)

app.include_router(health_router)
app.include_router(kanji_router)
app.include_router(ocr_router)
app.include_router(tokenization_router)
app.include_router(word_router)
app.include_router(translation_router)
app.include_router(vocabulary_router)
