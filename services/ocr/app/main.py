from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.ocr import router as ocr_router
from app.api.translation import router as translation_router

app = FastAPI(title="YomiMado local OCR service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",  # macOS app window
        "http://tauri.localhost",  # Windows app window
        "http://localhost:1420",  # Vite development server
        "http://127.0.0.1:1420",
    ],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(ocr_router)
app.include_router(translation_router)
