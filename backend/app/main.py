"""FastAPI application entry point.

Constitution VII: request bodies validated by Pydantic before this code runs;
no request text is ever logged (no logging statement here touches `request`);
ProviderError is mapped to HTTP status without leaking its provider's secrets.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api import benchmark, dialect, pronunciation, tts, voices
from backend.app.providers.registry import get_registry

app = FastAPI(title="Arabic TTS Prototype", version="0.1.0")
app.include_router(tts.router)
app.include_router(voices.router)
app.include_router(benchmark.router)
app.include_router(pronunciation.router)
app.include_router(dialect.router)

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/health")
async def health() -> dict:
    registry = get_registry()
    return {"status": "ok", "providers_available": len(registry.available())}


if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
