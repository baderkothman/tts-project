"""Deterministic test double (research R9).

Gives the offline suite precise control over chunk count, delay, timeout, and
mid-stream failure — control a recorded-cassette approach cannot offer.
Registered as a normal `TTSProvider`, so the conformance suite exercises it too.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider

_SILENT_MP3_FRAME = bytes(
    [0xFF, 0xFB, 0x90, 0x00] + [0x00] * 32
)  # a syntactically plausible (silent) MP3 frame, not a real encoder


class FakeProvider(TTSProvider):
    id = "fake"
    display_name = "Fake (test double)"

    def __init__(
        self,
        *,
        chunk_count: int = 5,
        chunk_delay_s: float = 0.0,
        fail_after_chunks: int | None = None,
        fail_kind: str = "server",
        status: ProviderStatus = ProviderStatus.AVAILABLE,
    ) -> None:
        self.chunk_count = chunk_count
        self.chunk_delay_s = chunk_delay_s
        self.fail_after_chunks = fail_after_chunks
        self.fail_kind = fail_kind
        self._status = status

    def available(self) -> ProviderStatus:
        return self._status

    def unavailable_reason(self) -> str | None:
        if self._status != ProviderStatus.AVAILABLE:
            return "FakeProvider configured unavailable for testing"
        return None

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            ssml=False,
            phoneme=False,
            native_emotions=False,
            prosody_rate=True,
            prosody_pitch=True,
            prosody_volume=True,
            locales=["ar-SA", "ar-EG"],
            formats=[AudioFormat.MP3_24KHZ],
            max_chars=5000,
            requires_credentials=False,
        )

    async def get_voices(self) -> list[VoiceConfig]:
        return [
            VoiceConfig(
                id="fake:ar-SA-female",
                provider=self.id,
                provider_voice_id="fake-voice-1",
                locale="ar-SA",
                gender="female",
                supports_streaming=True,
            )
        ]

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        if self._status != ProviderStatus.AVAILABLE:
            raise ProviderError(self.id, "unavailable", "provider not available")

        for i in range(self.chunk_count):
            if self.fail_after_chunks is not None and i >= self.fail_after_chunks:
                raise ProviderError(self.id, self.fail_kind, "simulated failure")  # type: ignore[arg-type]
            if self.chunk_delay_s:
                await asyncio.sleep(self.chunk_delay_s)
            yield _SILENT_MP3_FRAME

    async def synthesize(self, request: ProviderRequest) -> bytes:
        chunks = [c async for c in self.stream(request)]
        return b"".join(chunks)
