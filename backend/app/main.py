"""FastAPI application entry point.

No request text is ever logged; ProviderError is mapped to HTTP status
without leaking secrets (Constitution VII).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api import speak
from backend.app.config import get_settings
from backend.app.providers.groq import GroqProvider

app = FastAPI(title="Saudi Arabic TTS Prototype", version="0.2.0")
app.include_router(speak.router)

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    provider = GroqProvider(api_key=settings.groq_api_key)
    return {"status": "ok", "provider_available": provider.available()}


if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
