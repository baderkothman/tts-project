"""Request/response shapes for POST /api/tts/avatar and friends.

Mirrors `models/tts.py`'s own convention exactly: `AvatarGenerationRequest`
is not bound directly by FastAPI (the endpoint is `multipart/form-data` so
the portrait file rides alongside the text fields) — it exists so
validation/defaulting lives in one place the API layer and the test suite
can both call, and the job manager takes one typed object instead of a
dozen loose arguments.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.data.dialects import DEFAULT_DIALECT_ID, DIALECT_BY_ID
from backend.app.data.emotions import DEFAULT_EMOTION, EmotionName
from backend.app.data.voice_design import DEFAULT_PITCH, Gender, Pitch
from backend.app.models.tts import MAX_INPUT_CHARS_HARD_CAP, Mode, Quality

AvatarJobStatus = Literal[
    "queued",
    "preprocessing",
    "generating_audio",
    "preparing_avatar",
    "generating_video",
    "encoding",
    "completed",
    "failed",
    "cancelled",
]

# A coarse, honest progress number per state — not a smooth/animated
# percentage. Real sub-stage progress (e.g. "40% of GPU frames rendered")
# would need an engine-level progress callback, which
# `services/avatar_engine.AvatarEngine.generate()`'s signature deliberately
# doesn't carry yet (see that module's docstring) — a documented future
# extension point, not faked here with an invented smooth number.
PROGRESS_BY_STATUS: dict[AvatarJobStatus, int] = {
    "queued": 0,
    "preprocessing": 5,
    "generating_audio": 15,
    "preparing_avatar": 35,
    "generating_video": 45,
    "encoding": 90,
    "completed": 100,
    "failed": 0,  # actual value frozen at whatever it was when the failure happened — see AvatarJob.progress
    "cancelled": 0,  # same
}

TERMINAL_STATUSES: frozenset[AvatarJobStatus] = frozenset({"completed", "failed", "cancelled"})


class AvatarGenerationRequest(BaseModel):
    text: str = Field(..., max_length=MAX_INPUT_CHARS_HARD_CAP)
    mode: Mode = "voice_design"
    dialect_id: str = DEFAULT_DIALECT_ID
    gender: Gender | None = None
    pitch: Pitch = DEFAULT_PITCH
    # clone mode — ref_audio itself travels as an UploadFile at the API
    # layer, exactly like TTSRequest's own ref_text/ref_audio split.
    ref_text: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    quality: Quality = "high"
    guidance_scale: float = Field(default=2.0, ge=1.0, le=4.0)
    emotion: EmotionName = DEFAULT_EMOTION
    # No ai_dialect_rewrite field here on purpose — same reasoning as
    # TTSRequest (see models/tts.py's module docstring). The AI dialect
    # rewrite step runs automatically in avatar_jobs.py::_run_job, gated
    # only on dialect_rewriter.is_configured(), *before* the TTSRequest for
    # the audio step is built — so the processed text, not the raw typed
    # text, is what actually gets spoken and cached.

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return v

    @field_validator("dialect_id")
    @classmethod
    def dialect_known(cls, v: str) -> str:
        if v not in DIALECT_BY_ID:
            raise ValueError(f"unknown dialect_id '{v}'; valid options: {sorted(DIALECT_BY_ID)}")
        return v


class AvatarJobCreateResponse(BaseModel):
    job_id: str
    status: AvatarJobStatus


class AvatarJobResponse(BaseModel):
    job_id: str
    status: AvatarJobStatus
    progress: int
    engine: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    duration: float | None = None
    processing_time: float | None = None
    # (kind, message) — same shape as every other typed error surface in
    # this app (InferenceError, DialectRewriteError, AvatarEngineError,
    # PortraitValidationError all collapse into this one pair here).
    error_kind: str | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: float
    updated_at: float


class AvatarJobEvent(BaseModel):
    """The SSE payload shape — a strict subset of `AvatarJobResponse` (just
    enough for a progress bar/status line), not the full response, so a
    long-lived stream doesn't repeat the (rarely-changing) request echo on
    every event. A client wanting the full shape re-fetches
    `GET /api/tts/avatar/jobs/{id}` once the stream reaches a terminal
    status."""

    job_id: str
    status: AvatarJobStatus
    progress: int
