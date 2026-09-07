"""Voice, dialect and capability models.

Nothing here imports a provider SDK (Constitution II).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Dialect(StrEnum):
    """Arabic dialect *family*, distinct from an exact locale.

    Only families a provider actually publishes a locale for are ever claimed
    (FR-027). Locales with no defensible family claim carry ``dialect=None``.
    """

    MSA = "msa"
    GULF = "gulf"
    EGYPTIAN = "egyptian"
    LEVANTINE = "levantine"
    MAGHREBI = "maghrebi"


class EmotionStyle(StrEnum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    WARM = "warm"
    CALM = "calm"
    SERIOUS = "serious"
    CONVERSATIONAL = "conversational"


class AudioFormat(StrEnum):
    MP3_24KHZ = "mp3_24khz"
    MP3_48KHZ = "mp3_48khz"
    PCM_16KHZ = "pcm_16khz"
    PCM_24KHZ = "pcm_24khz"
    OPUS_24KHZ = "opus_24khz"

    @property
    def content_type(self) -> str:
        if self.name.startswith("MP3"):
            return "audio/mpeg"
        if self.name.startswith("PCM"):
            return "audio/wave"
        return "audio/ogg"


class ProviderStatus(StrEnum):
    AVAILABLE = "available"
    MISSING_CREDENTIALS = "missing_credentials"
    UNREACHABLE = "unreachable"


class VoiceConfig(BaseModel):
    """A speaking identity offered by one provider."""

    id: str
    provider: str
    provider_voice_id: str
    language: str = "ar"
    locale: str
    dialect: Dialect | None = None
    gender: str
    supports_streaming: bool = True
    supports_emotions: bool = False
    supports_ssml: bool = False
    latency_class: str | None = None
    fallback_voice_id: str | None = None
    display_name: str = ""


class Capabilities(BaseModel):
    """Declared abilities of a provider.

    The router branches on these fields and never on a provider's name; that is
    the mechanical guarantee behind Constitution II and SC-010.
    """

    streaming: bool = False
    ssml: bool = False
    phoneme: bool = False
    native_emotions: bool = False
    prosody_rate: bool = False
    prosody_pitch: bool = False
    prosody_volume: bool = False
    locales: list[str] = Field(default_factory=list)
    formats: list[AudioFormat] = Field(default_factory=list)
    max_chars: int = 5000
    requires_credentials: bool = True
    notes: str = ""


class ProviderInfo(BaseModel):
    id: str
    display_name: str
    status: ProviderStatus
    capabilities: Capabilities
    voice_count: int
    unavailable_reason: str | None = None
