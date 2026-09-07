"""Request/response models for synthesis (FR-004, FR-006, FR-007, data-model.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.models.voice import Gender, Voice

MAX_INPUT_CHARS = 5000


class SpeechRequest(BaseModel):
    text: str = Field(..., max_length=MAX_INPUT_CHARS)
    voice_id: str | None = None
    gender: Literal["male", "female"] | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        # Stripping first makes whitespace-only input a validation error
        # rather than a silent empty synthesis (FR-004).
        if not v.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return v


class LatencyInfo(BaseModel):
    generation_ms: float
    audio_duration_ms: float
    real_time_factor: float


class SpeechResponse(BaseModel):
    audio_base64: str
    content_type: str
    voice: Voice
    latency: LatencyInfo


__all__ = ["SpeechRequest", "SpeechResponse", "LatencyInfo", "Gender"]
