"""ElevenLabs adapter (research R1). Credential-gated, SSE streaming.

ElevenLabs publishes no Arabic locale codes (research R2), so its voices carry
dialect=None rather than an inferred family (FR-027). Phoneme tags are
English-only on this provider (research R4), so capabilities().phoneme is
False for Arabic even though the vendor supports phonemes generally.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from backend.app.config import Settings
from backend.app.data.voices import ELEVENLABS_VOICES
from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.text_processing.provider_formatting import prosody_for_style

_BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsProvider(TTSProvider):
    id = "elevenlabs"
    display_name = "ElevenLabs"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            ssml=False,
            # Phoneme (IPA/CMU) tags are English-only on ElevenLabs; Arabic
            # correction here is alias/orthographic substitution only
            # (research R4).
            phoneme=False,
            native_emotions=True,  # voice-settings style/stability, not SSML
            prosody_rate=False,
            prosody_pitch=False,
            prosody_volume=False,
            locales=[],  # no documented Arabic locale codes (FR-027)
            formats=[AudioFormat.MP3_24KHZ, AudioFormat.OPUS_24KHZ],
            max_chars=5000,
            requires_credentials=True,
        )

    def available(self) -> ProviderStatus:
        if self._settings.has_elevenlabs():
            return ProviderStatus.AVAILABLE
        return ProviderStatus.MISSING_CREDENTIALS

    def unavailable_reason(self) -> str | None:
        if not self._settings.has_elevenlabs():
            return "Set ELEVENLABS_API_KEY to enable this provider"
        return None

    async def get_voices(self) -> list[VoiceConfig]:
        return list(ELEVENLABS_VOICES)

    def _voice_settings(self, request: ProviderRequest) -> dict:
        # Style is mapped onto ElevenLabs' voice-settings knobs rather than
        # SSML prosody, since this adapter accepts no SSML.
        rate_pct, _, _ = prosody_for_style(request.emotion)
        style_amount = min(1.0, max(0.0, 0.3 + rate_pct / 100))
        return {"stability": 0.5, "similarity_boost": 0.75, "style": style_amount}

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        if not self._settings.has_elevenlabs():
            raise ProviderError(self.id, "auth", "ElevenLabs API key not configured")

        url = f"{_BASE_URL}/text-to-speech/{request.voice.provider_voice_id}/stream"
        headers = {
            "xi-api-key": self._settings.elevenlabs_api_key or "",
            "Content-Type": "application/json",
        }
        payload = {
            "text": request.text,
            "model_id": self._settings.elevenlabs_model_id,
            "voice_settings": self._voice_settings(request),
        }
        try:
            async with httpx.AsyncClient(timeout=request.timeout_s) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code == 401:
                        raise ProviderError(self.id, "auth", "ElevenLabs rejected the API key")
                    if resp.status_code == 429:
                        raise ProviderError(self.id, "rate_limit", "ElevenLabs rate limit exceeded")
                    if resp.status_code >= 500:
                        raise ProviderError(self.id, "server", f"ElevenLabs server error {resp.status_code}")
                    if resp.status_code >= 400:
                        raise ProviderError(self.id, "bad_request", f"ElevenLabs rejected request: {resp.status_code}")
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.TimeoutException as exc:
            raise ProviderError(self.id, "timeout", "ElevenLabs request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(self.id, "unavailable", "ElevenLabs unreachable") from exc

    async def synthesize(self, request: ProviderRequest) -> bytes:
        chunks = [c async for c in self.stream(request)]
        return b"".join(chunks)
