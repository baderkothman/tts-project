"""FastAPI application entry point.

Loads `oddadmix/lahgtna-omnivoice-v2` exactly once, at startup, via
`TTSEngine.load()` run off the event loop in a worker thread — the process
accepts `/api/health` immediately and reports `status: "loading"` until the
one-time load (weight download on first run, then just weight loading)
finishes, rather than blocking the whole server on it.

No request text or generated audio is ever logged.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import tts
from backend.app.config import get_settings
from backend.app.services.inference import TTSEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lahgtna.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = TTSEngine(settings)
    app.state.engine = engine

    async def _load() -> None:
        try:
            await asyncio.to_thread(engine.load)
        except Exception:  # noqa: BLE001 - already logged in TTSEngine.load
            logger.error("Model failed to load — /api/tts will return 503 until this is fixed")

    load_task = asyncio.create_task(_load())
    try:
        yield
    finally:
        load_task.cancel()


app = FastAPI(
    title="لهجتنا — Arabic Dialect TTS",
    description="Arabic dialect text-to-speech, powered exclusively by oddadmix/lahgtna-omnivoice-v2.",
    version="0.3.0",
    lifespan=lifespan,
)

# Dev-time convenience only: allows `vite dev` on a different port to reach
# the API directly. In production the frontend build is served from this
# same origin (mounted below), so this never matters there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tts.router)

_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
