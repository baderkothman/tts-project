"""Azure AI Speech adapter (research R1). Credential-gated.

Azure serves the same underlying neural voice family as the Edge adapter but
exposes a real API contract: SSML with prosody and Arabic <phoneme> support
(research R4) — the one adapter in this project that can honour a
provider-scoped phoneme PronunciationRule.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from backend.app.config import Settings
from backend.app.data.voices import AZURE_VOICES
from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.text_processing.provider_formatting import build_ssml, prosody_for_style

_FORMAT_HEADER = {
    AudioFormat.MP3_24KHZ: "audio-24khz-48kbitrate-mono-mp3",
    AudioFormat.MP3_48KHZ: "audio-48khz-96kbitrate-mono-mp3",
    AudioFormat.PCM_16KHZ: "raw-16khz-16bit-mono-pcm",
    AudioFormat.PCM_24KHZ: "raw-24khz-16bit-mono-pcm",
    AudioFormat.OPUS_24KHZ: "audio-24khz-48kbitrate-mono-mp3",  # fallback
}


class AzureProvider(TTSProvider):
    id = "azure"
    display_name = "Azure AI Speech"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            ssml=True,
            phoneme=True,
            # No Azure Arabic voice exposes speaking styles or roles
            # (research R2, verified against the published voice table).
            native_emotions=False,
            prosody_rate=True,
            prosody_pitch=True,
            prosody_volume=True,
            locales=sorted({v.locale for v in AZURE_VOICES}),
            formats=list(_FORMAT_HEADER.keys()),
            max_chars=5000,
            requires_credentials=True,
        )

    def available(self) -> ProviderStatus:
        if self._settings.has_azure():
            return ProviderStatus.AVAILABLE
        return ProviderStatus.MISSING_CREDENTIALS

    def unavailable_reason(self) -> str | None:
        if not self._settings.has_azure():
            return "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to enable this provider"
        return None

    async def get_voices(self) -> list[VoiceConfig]:
        return list(AZURE_VOICES)

    def _endpoint(self) -> str:
        region = self._settings.azure_speech_region
        return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        if not self._settings.has_azure():
            raise ProviderError(self.id, "auth", "Azure credentials not configured")

        rate_pct, pitch_pct, vol_pct = prosody_for_style(request.emotion)
        ssml = build_ssml(
            request.text,
            request.voice,
            rate=f"{rate_pct:+.0f}%",
            pitch=f"{pitch_pct:+.0f}%",
            volume=f"{vol_pct:+.0f}%",
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._settings.azure_speech_key or "",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": _FORMAT_HEADER.get(
                request.output_format, _FORMAT_HEADER[AudioFormat.MP3_24KHZ]
            ),
            "User-Agent": "arabic-tts-prototype",
        }
        try:
            async with httpx.AsyncClient(timeout=request.timeout_s) as client:
                async with client.stream(
                    "POST", self._endpoint(), content=ssml.encode("utf-8"), headers=headers
                ) as resp:
                    if resp.status_code == 401:
                        raise ProviderError(self.id, "auth", "Azure rejected the subscription key")
                    if resp.status_code == 429:
                        raise ProviderError(self.id, "rate_limit", "Azure rate limit exceeded")
                    if resp.status_code >= 500:
                        raise ProviderError(self.id, "server", f"Azure server error {resp.status_code}")
                    if resp.status_code >= 400:
                        raise ProviderError(self.id, "bad_request", f"Azure rejected request: {resp.status_code}")
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.TimeoutException as exc:
            raise ProviderError(self.id, "timeout", "Azure request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(self.id, "unavailable", "Azure unreachable") from exc

    async def synthesize(self, request: ProviderRequest) -> bytes:
        chunks = [c async for c in self.stream(request)]
        return b"".join(chunks)
