"""Request/response models for synthesis, plus pronunciation data types."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.app.models.voice import AudioFormat, Dialect, EmotionStyle, VoiceConfig

MAX_INPUT_CHARS = 5000
LOCALE_PATTERN = r"^[a-z]{2}-[A-Z]{2}$"


class TTSRequest(BaseModel):
    """A synthesis request.

    ``apply_preprocessing`` and ``apply_pronunciation`` are separate switches so
    the before/after demonstration can hold everything else constant and vary
    only the correction (FR-020).
    """

    text: str = Field(..., max_length=MAX_INPUT_CHARS)
    locale: str | None = Field(default=None, pattern=LOCALE_PATTERN)
    dialect: Dialect | None = None
    provider: str | None = None
    voice_id: str | None = None
    emotion: EmotionStyle = EmotionStyle.NEUTRAL
    speaking_rate: float | None = Field(default=None, ge=0.5, le=2.0)
    pitch: float | None = Field(default=None, ge=-20.0, le=20.0)
    output_format: AudioFormat = AudioFormat.MP3_24KHZ
    apply_preprocessing: bool = True
    apply_pronunciation: bool = True
    client_t0_ms: float | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        # Stripping first is what makes whitespace-only input a validation
        # error rather than a silent empty synthesis (FR-003).
        if not v.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return v


class StageDiff(BaseModel):
    """What one pipeline stage did. Makes the pipeline inspectable (FR-016)."""

    stage_name: str
    before: str
    after: str
    changed: bool
    duration_ms: float


class ProcessedText(BaseModel):
    original: str
    processed: str
    stages: list[StageDiff] = Field(default_factory=list)
    changed: bool = False


class LatencyReport(BaseModel):
    """Per-request timings.

    ``client_ttfa_ms`` is nullable because it depends on a clock the server does
    not own; reporting a server figure under that name would be false precision.
    """

    preprocessing_ms: float | None = None
    provider_ttfa_ms: float | None = None
    backend_ttfa_ms: float | None = None
    total_generation_ms: float | None = None
    audio_duration_ms: float | None = None
    real_time_factor: float | None = None
    client_ttfa_ms: float | None = None


class TTSResponse(BaseModel):
    audio_base64: str
    content_type: str
    processed_text: ProcessedText
    voice: VoiceConfig
    provider: str
    emotion_applied: EmotionStyle
    emotion_native: bool
    used_fallback: bool = False
    fallback_reason: str | None = None
    latency: LatencyReport
    audio_duration_ms: float | None = None


class PronunciationRule(BaseModel):
    """A correction expressed as data, never as a code branch (FR-018).

    ``whole_word`` defaults True because Arabic attaches prefixes (و، ال، ب، ل)
    freely; a naive substring rule would corrupt unrelated words, which is a
    meaning change and forbidden by Constitution III.
    """

    original: str
    replacement: str
    locale: str | None = None
    provider: str | None = None
    notes: str | None = None
    category: str = "general"
    whole_word: bool = True


class PronunciationDemo(BaseModel):
    """A genuinely observed defect.

    ``provider_observed`` and ``voice_observed`` are required, not optional:
    FR-019 and Constitution V demand the defect be traceable to an actual
    synthesis, and a nullable field would let an undocumented claim through.
    """

    original_text: str
    observed_pronunciation: str
    desired_pronunciation: str
    correction_technique: str
    corrected_text: str
    provider_observed: str
    voice_observed: str
    explanation: str
