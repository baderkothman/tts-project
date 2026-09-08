"""FastAPI application entry point.

Loads every model exactly once, at startup, each off the event loop in its
own worker thread so they load in parallel rather than one after another:
`oddadmix/lahgtna-omnivoice-v2` (required — `/api/tts` 503s until it's
ready), the Fine-Tashkeel diacritizer, and Kokoro (English TTS for the
`dual_model` pipeline mode). The latter two are best-effort: a failure
there degrades gracefully (diacritization is skipped, `dual_model` falls
back to `native`) rather than blocking the whole app on a non-essential
model. `/api/health` responds immediately regardless.

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
from backend.app.services import diacritizer, english_tts
from backend.app.services.inference import TTSEngine
from backend.app.services.speech_pipeline import SpeechPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lahgtna.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # `transformers` lazily binds most of its submodule attributes on first
    # access (a `LazyModule.__getattr__`); triggering that resolution here,
    # once, on the main thread, before the three loaders below run
    # concurrently in their own threads avoids a real race hit during this
    # feature's own development — two threads independently resolving a
    # transformers submodule name for the first time at the same moment
    # raised a spurious `ImportError: cannot import name 'AlbertModel'`
    # that did not reproduce when importing it a second time.
    import transformers

    for _name in ("AutoTokenizer", "AutoModelForSeq2SeqLM", "AlbertModel"):
        getattr(transformers, _name)

    settings = get_settings()
    engine = TTSEngine(settings)
    app.state.engine = engine
    app.state.pipeline = SpeechPipeline(engine)

    async def _load_arabic() -> None:
        try:
            await asyncio.to_thread(engine.load)
        except Exception:  # noqa: BLE001 - already logged in TTSEngine.load
            logger.error("Lahgtna failed to load — /api/tts will return 503 until this is fixed")

    async def _load_diacritizer() -> None:
        try:
            await asyncio.to_thread(diacritizer.load)
        except Exception:  # noqa: BLE001
            logger.warning("Diacritizer failed to load — Arabic text will be spoken undiacritized")

    async def _load_english_tts() -> None:
        await asyncio.to_thread(english_tts.load)  # never raises — records load_error() instead

    tasks = [
        asyncio.create_task(_load_arabic()),
        asyncio.create_task(_load_diacritizer()),
        asyncio.create_task(_load_english_tts()),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()


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
