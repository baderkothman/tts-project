"""Request/response shapes for POST /api/tts and friends.

`TTSRequest` is not bound directly by FastAPI (the endpoint accepts
`multipart/form-data` so an optional reference-audio file can ride alongside
the text fields) — it exists so validation and defaulting live in one place
that both the API layer and the test suite can call directly, and so the
service layer takes a single typed object instead of eight loose arguments.

No `ai_dialect_rewrite` field here on purpose: the AI dialect rewrite step
(`services/dialect_rewriter.py`) is no longer a per-request opt-in. It now
runs automatically inside `SpeechPipeline.synthesize()`/`synthesize_stream()`,
gated only on `dialect_rewriter.is_configured()` (i.e. whether
`OPENAI_API_KEY` is set server-side) — never on anything the client sends,
and never while the user is just typing (`/api/preprocess` below never calls
it at all). See `dialect_rewriter.py`'s module docstring for the full
rationale.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.data.dialects import DEFAULT_DIALECT_ID, DIALECT_BY_ID
from backend.app.data.voice_design import DEFAULT_PITCH, Gender, Pitch

MAX_INPUT_CHARS_HARD_CAP = 2000  # mirrors Settings.max_input_chars default; see config.py

# "fast" -> num_step=16 (the model card's own suggested faster setting),
# "high" -> num_step=32 (the model's default). Not a fabricated knob: both
# values are the two figures OmniVoice's own docs give for this trade-off.
Quality = Literal["fast", "high"]

Mode = Literal["voice_design", "clone", "auto"]

# How mixed Arabic/English text gets spoken — see services/speech_pipeline.py
# and docs/ENGLISH_TTS_EVALUATION.md for the measured reasoning behind
# "native" (Lahgtna alone) being the default rather than "dual_model".
#   native:          one Lahgtna call; English words spoken as Lahgtna itself renders them.
#   dual_model:      Arabic segments -> Lahgtna, English segments -> Kokoro, then stitched.
#   transliteration: English segments rewritten to Arabic-script phonetics first, then one Lahgtna call.
PipelineMode = Literal["native", "dual_model", "transliteration"]


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=MAX_INPUT_CHARS_HARD_CAP)
    mode: Mode = "voice_design"
    pipeline_mode: PipelineMode = "native"

    # voice_design mode
    dialect_id: str = DEFAULT_DIALECT_ID
    gender: Gender | None = None
    pitch: Pitch = DEFAULT_PITCH

    # clone mode — ref_audio itself travels as an UploadFile at the API
    # layer, not through this model; ref_text does not.
    ref_text: str | None = None

    # shared generation controls
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    quality: Quality = "high"
    guidance_scale: float = Field(default=2.0, ge=1.0, le=4.0)

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
            raise ValueError(
                f"unknown dialect_id '{v}'; valid options: {sorted(DIALECT_BY_ID)}"
            )
        return v


class LatencyInfo(BaseModel):
    generation_ms: float
    audio_duration_ms: float
    real_time_factor: float


class SegmentInfo(BaseModel):
    """One Arabic or English run of the input — mirrors
    `services.text_preprocessor.SegmentPreview` as a wire-serializable
    shape, for the "what will actually be spoken" UI preview."""

    language: Literal["ar", "en"]
    original_text: str
    speak_text: str
    diacritized: bool = False


class PreprocessRequest(BaseModel):
    """The live "what will actually be spoken" preview, as the user types —
    deliberately local-only. No AI dialect rewrite field here: that step
    calls OpenAI (a real, metered API), so it only ever runs once, at actual
    generation time (see `TTSRequest`'s module docstring) — never per
    keystroke or per dialect selection. This preview can therefore
    legitimately show slightly different wording than what ends up spoken;
    `TTSResponse.processed_text` (returned from a real generation) is what's
    authoritative for what was actually said."""

    text: str = Field(..., max_length=MAX_INPUT_CHARS_HARD_CAP)
    dialect_id: str = DEFAULT_DIALECT_ID
    pipeline_mode: PipelineMode = "native"

    @field_validator("dialect_id")
    @classmethod
    def dialect_known(cls, v: str) -> str:
        if v not in DIALECT_BY_ID:
            raise ValueError(f"unknown dialect_id '{v}'; valid options: {sorted(DIALECT_BY_ID)}")
        return v


class PreprocessResponse(BaseModel):
    original_text: str
    processed_text: str
    segments: list[SegmentInfo]
    warnings: list[str] = Field(default_factory=list)


class TTSResponse(BaseModel):
    audio_base64: str
    content_type: str = "audio/wav"
    sample_rate: int
    mode: Mode
    pipeline_mode: PipelineMode
    dialect_id: str | None
    gender: Gender | None
    latency: LatencyInfo
    # The pronunciation-ready text and per-segment breakdown actually used
    # for this generation — the same shape /api/preprocess returns, so the
    # UI can show one "what will be spoken" panel from either call.
    processed_text: str
    segments: list[SegmentInfo]
    # Honest, non-fatal notices surfaced to the UI — e.g. a dialect that
    # falls back to language-agnostic mode (see data/dialects.py). Empty in
    # the common case.
    warnings: list[str] = Field(default_factory=list)


class ModelCapabilities(BaseModel):
    voice_design: bool
    voice_cloning: bool
    dialect_control: bool
    diacritics_aware: bool
    named_voice_roster: bool  # always False — see data/README note in api/tts.py
    automatic_diacritization: bool
    mixed_language_support: bool


class ModelInfo(BaseModel):
    repo_id: str
    architecture: str
    base_model: str
    device: str
    sample_rate: int
    dialects_supported: int
    capabilities: ModelCapabilities
    pipeline_modes: list[PipelineMode]
    diacritizer_loaded: bool
    english_tts_loaded: bool
    # No load state to report (nothing loads at startup) — just whether
    # OPENAI_API_KEY is set server-side. Informational only: there is no
    # per-request toggle to grey out anymore — when this is true, every
    # /api/tts (and avatar) generation automatically gets the AI dialect
    # rewrite step; when false, it's silently skipped. See
    # services/dialect_rewriter.is_configured().
    dialect_rewriter_configured: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "loading", "error"]
    model_loaded: bool
    device: str | None = None
    detail: str | None = None
