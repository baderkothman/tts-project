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

from backend.app.api import avatar, tts
from backend.app.config import get_settings
from backend.app.services import diacritizer, english_tts
from backend.app.services.avatar_engine import AvatarEngine
from backend.app.services.avatar_engines.replicate_engine import ReplicateAvatarEngine
from backend.app.services.avatar_engines.stub_engine import StubAvatarEngine
from backend.app.services.avatar_jobs import AvatarJobManager
from backend.app.services.inference import TTSEngine
from backend.app.services.speech_pipeline import SpeechPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lahgtna.main")


def _select_avatar_engine(settings) -> AvatarEngine:
    """Same "optional credential, honest fallback" shape
    `dialect_rewriter.is_configured()` uses for `OPENAI_API_KEY`: real AI
    lip sync (`ReplicateAvatarEngine`, see its module docstring) when
    `REPLICATE_API_TOKEN` is set, the free procedural placeholder
    (`StubAvatarEngine`) otherwise — never a hard failure to start the app
    over a missing optional, metered credential."""
    if settings.replicate_api_token:
        logger.info("Talking Avatar: using ReplicateAvatarEngine (real AI lip sync)")
        return ReplicateAvatarEngine(settings.replicate_api_token)
    logger.info("Talking Avatar: REPLICATE_API_TOKEN not set — using StubAvatarEngine (procedural placeholder)")
    return StubAvatarEngine()


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

    # Talking Avatar job manager — see services/avatar_jobs.py's module
    # docstring for why this is in-process rather than Celery/Redis.
    # Started/stopped explicitly (not just constructed) so its background
    # worker/cleanup tasks are cancelled cleanly on shutdown rather than
    # left dangling.
    avatar_jobs = AvatarJobManager(pipeline=app.state.pipeline, engine=_select_avatar_engine(settings), settings=settings)
    avatar_jobs.start()
    app.state.avatar_jobs = avatar_jobs

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
        await avatar_jobs.stop()


app = FastAPI(
    title="لهجتنا — Arabic Dialect TTS",
    description="Arabic dialect text-to-speech, powered exclusively by oddadmix/lahgtna-omnivoice-v2.",
    version="0.3.0",
    lifespan=lifespan,
)

# The two dev-server origins are always allowed (Vite's own :5173) — that
# never depends on configuration, same as before this app supported a split
# deployment. `CORS_ALLOWED_ORIGINS` (config.py's cors_allowed_origins_list)
# adds to that list — set it to a split frontend service's public URL (see
# frontend/Dockerfile's own docstring) once the frontend isn't served from
# this same origin (the StaticFiles mount below) anymore. Empty by default,
# so the single-container deployment mode needs no extra configuration.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *get_settings().cors_allowed_origins_list,
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tts.router)
app.include_router(avatar.router)

_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
