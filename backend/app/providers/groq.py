"""Groq Orpheus Arabic (Saudi dialect) adapter — this feature's sole provider
(research.md R1). Ported from the prior feature's adapter with the same
chunking/stitching/error-mapping logic (research.md R2: nothing about the
vendor's real constraints changed, only the surrounding Voice/ProviderError
shape did).

Real API constraints, established by live testing in the prior feature:
  - The API caps `input` at 200 characters per call — this adapter chunks
    the text into <=200-char, word-boundary-safe segments and stitches the
    resulting WAV files into one valid WAV using the `wave` module (never
    by naive byte concatenation, which produces a multi-header file most
    decoders reject after the first segment).
  - Voice names must be lowercase in the API call, despite the vendor's own
    docs page showing them capitalized.
  - **10 requests/minute** on this model (on-demand tier) — not documented,
    found only by exceeding it live. One `Retry-After`-honoring retry
    absorbs a transient hit; a second failure still raises so the caller
    can report it clearly (FR-008).
"""

from __future__ import annotations

import asyncio
import io
import re
import wave

import httpx

from backend.app.models.voice import Voice
from backend.app.providers.base import ProviderError, TTSProvider

_ENDPOINT = "https://api.groq.com/openai/v1/audio/speech"
_MODEL = "canopylabs/orpheus-arabic-saudi"
_MAX_SEGMENT_CHARS = 200

_BOUNDARY_PATTERN = re.compile(r"(?<=[.؟!])\s+|(?<=،)\s+")


def _chunk_text(text: str, limit: int = _MAX_SEGMENT_CHARS) -> list[str]:
    """Split `text` into <=`limit`-char segments, never mid-word."""
    sentences = [s for s in _BOUNDARY_PATTERN.split(text) if s]
    segments: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            segments.append(current)
            current = ""

    for sentence in sentences:
        words = sentence.split(" ")
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if len(candidate) <= limit:
                current = candidate
            else:
                flush()
                if len(word) <= limit:
                    current = word
                else:
                    segments.append(word)
    flush()
    return segments or [""]


def _concat_wav(wav_blobs: list[bytes]) -> bytes:
    if len(wav_blobs) == 1:
        return wav_blobs[0]
    out = io.BytesIO()
    writer: wave.Wave_write | None = None
    try:
        for blob in wav_blobs:
            with wave.open(io.BytesIO(blob), "rb") as reader:
                if writer is None:
                    writer = wave.open(out, "wb")
                    writer.setnchannels(reader.getnchannels())
                    writer.setsampwidth(reader.getsampwidth())
                    writer.setframerate(reader.getframerate())
                writer.writeframes(reader.readframes(reader.getnframes()))
    finally:
        if writer is not None:
            writer.close()
    return out.getvalue()


class GroqProvider(TTSProvider):
    id = "groq"
    display_name = "Groq — Orpheus Arabic (Saudi dialect)"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def available(self) -> bool:
        return bool(self._api_key)

    def unavailable_reason(self) -> str | None:
        if not self._api_key:
            return "Set GROQ_API_KEY to enable this provider"
        return None

    async def list_voices(self) -> list[Voice]:
        from backend.app.data.voices import GROQ_VOICES

        return list(GROQ_VOICES)

    async def _synthesize_segment(self, client: httpx.AsyncClient, text: str, provider_voice_id: str) -> bytes:
        headers = {
            "Authorization": f"Bearer {self._api_key or ''}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _MODEL,
            "voice": provider_voice_id,
            "input": text,
            "response_format": "wav",
        }

        for attempt in range(2):
            resp = await client.post(_ENDPOINT, json=payload, headers=headers)
            if resp.status_code == 429 and attempt == 0:
                retry_after = min(float(resp.headers.get("retry-after", 5)), 15.0)
                await asyncio.sleep(retry_after)
                continue
            break

        if resp.status_code == 401:
            raise ProviderError(self.id, "auth", "Groq rejected the API key")
        if resp.status_code == 429:
            raise ProviderError(
                self.id, "rate_limit",
                "Groq rate limit exceeded (10 requests/minute on this model, per vendor response)",
            )
        if resp.status_code >= 500:
            raise ProviderError(self.id, "server", f"Groq server error {resp.status_code}")
        if resp.status_code >= 400:
            raise ProviderError(self.id, "bad_request", f"Groq rejected request: {resp.status_code}")
        return resp.content

    async def synthesize(self, text: str, voice: Voice, *, timeout_s: float) -> bytes:
        if not self._api_key:
            raise ProviderError(self.id, "auth", "Groq credentials not configured")

        segments = _chunk_text(text)
        # The vendor API requires lowercase voice names, despite its own
        # docs page showing them capitalized (live-discovered in the prior
        # feature) — `voice.name` is the display form ("Abdullah"); derive
        # the API value from it rather than storing a near-duplicate field.
        provider_voice_id = voice.name.lower()
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                blobs = [
                    await self._synthesize_segment(client, segment, provider_voice_id)
                    for segment in segments
                ]
        except httpx.TimeoutException as exc:
            raise ProviderError(self.id, "timeout", "Groq request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(self.id, "server", "Groq unreachable") from exc

        return _concat_wav(blobs)
