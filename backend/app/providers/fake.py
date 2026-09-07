"""Deterministic test double (Constitution VIII — offline-testable by default)."""

from __future__ import annotations

from backend.app.models.voice import Voice
from backend.app.providers.base import ErrorKind, ProviderError, TTSProvider

FAKE_VOICES = [
    Voice(id="fake:male-1", name="Test Male", provider="fake", gender="male", model="fake-model"),
    Voice(id="fake:female-1", name="Test Female", provider="fake", gender="female", model="fake-model"),
]


class FakeProvider(TTSProvider):
    id = "fake"
    display_name = "Fake (test double)"

    def __init__(self, *, fail_kind: ErrorKind | None = None) -> None:
        self._fail_kind = fail_kind

    async def list_voices(self) -> list[Voice]:
        return list(FAKE_VOICES)

    async def synthesize(self, text: str, voice: Voice, *, timeout_s: float) -> bytes:
        if self._fail_kind is not None:
            raise ProviderError(self.id, self._fail_kind, f"induced {self._fail_kind} failure")
        # A minimal valid WAV (44-byte header + a little silence) so
        # duration-from-frames logic has something real to measure.
        import io
        import wave

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00" * 2400)  # 0.1s of silence
        return buf.getvalue()
