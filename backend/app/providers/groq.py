"""Groq Orpheus Arabic (Saudi dialect) adapter (research R1). Credential-gated.

Unlike Edge/ElevenLabs, this is a genuinely dialect-trained model rather than
an MSA-trained voice pressed into service as "Arabic": Groq documents
`canopylabs/orpheus-arabic-saudi` as producing authentic Saudi/Gulf colloquial
speech, not Modern Standard Arabic (research R1, docs fetched 2026-09-07).
Voices therefore carry ``dialect=Dialect.GULF``, not ``Dialect.MSA``, even
though their locale is ``ar-SA`` — locale and dialect are independent fields
in this catalogue precisely so this distinction can be made (FR-027).

Three real API constraints shape this adapter — the first two documented by
the vendor, the third discovered only by exceeding it live:
  - The API caps `input` at 200 characters per call (Groq docs, Orpheus
    model page) — far below the pipeline's 5000-character request limit. This
    adapter chunks the processed text into <=200-char, word-boundary-safe
    segments, calls the endpoint once per segment, and stitches the resulting
    WAV files into a single valid WAV using the `wave` module (never by
    naive byte concatenation, which produces a file with multiple headers
    that most decoders reject after the first segment).
  - No streaming or vocal-direction (style-tag) capability is documented for
    the Arabic model, unlike the English Orpheus model. `capabilities()`
    reports both as False rather than assumed (Constitution V).
  - **10 requests/minute** on this model (on-demand tier) — not in the docs
    fetched during research; found by live-testing once a key was configured.
    A single `Retry-After`-honoring retry absorbs a transient hit; a second
    failure still raises a retryable `ProviderError` so the caller's own
    fallback (services/tts_service.py) can take over.
"""

from __future__ import annotations

import asyncio
import io
import re
import wave
from collections.abc import AsyncIterator

import httpx

from backend.app.config import Settings
from backend.app.data.voices import GROQ_VOICES
from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider

_ENDPOINT = "https://api.groq.com/openai/v1/audio/speech"
_MODEL = "canopylabs/orpheus-arabic-saudi"
_MAX_SEGMENT_CHARS = 200

# Sentence/clause boundaries to prefer when splitting, in priority order:
# Arabic full stop and question mark, Arabic comma, then plain whitespace as
# the fallback so a segment never splits inside a word.
_BOUNDARY_PATTERN = re.compile(r"(?<=[.؟!])\s+|(?<=،)\s+")


def _chunk_text(text: str, limit: int = _MAX_SEGMENT_CHARS) -> list[str]:
    """Split `text` into <=`limit`-char segments, never mid-word.

    Splits at sentence boundaries first; a sentence still over the limit is
    further split at whitespace. A single word longer than `limit` (no
    whitespace to split on) is emitted whole rather than corrupted mid-word.
    """
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
                    segments.append(word)  # single word exceeds limit; emit as-is
    flush()
    return segments or [""]


def _concat_wav(wav_blobs: list[bytes]) -> bytes:
    """Merge sequential WAV files into one valid WAV (matching parameters)."""
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

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=False,  # not documented for the Arabic Orpheus model
            ssml=False,
            phoneme=False,
            native_emotions=False,  # vocal-direction tags are English-model-only
            prosody_rate=False,
            prosody_pitch=False,
            prosody_volume=False,
            locales=sorted({v.locale for v in GROQ_VOICES}),
            # Vendor confirms WAV output but not a fixed sample rate; PCM_24KHZ
            # is reported as the nearest catalogued format, not a verified rate.
            formats=[AudioFormat.PCM_24KHZ],
            max_chars=5000,  # enforced pipeline-side; this adapter chunks internally
            requires_credentials=True,
            notes="canopylabs/orpheus-arabic-saudi: authentic Saudi/Gulf dialect, "
            "not MSA. 200-char API limit per call, chunked transparently by "
            "this adapter. No streaming or style-tag support documented.",
        )

    def available(self) -> ProviderStatus:
        if self._settings.has_groq():
            return ProviderStatus.AVAILABLE
        return ProviderStatus.MISSING_CREDENTIALS

    def unavailable_reason(self) -> str | None:
        if not self._settings.has_groq():
            return "Set GROQ_API_KEY to enable this provider"
        return None

    async def get_voices(self) -> list[VoiceConfig]:
        return list(GROQ_VOICES)

    async def _synthesize_segment(self, client: httpx.AsyncClient, text: str, voice: VoiceConfig) -> bytes:
        headers = {
            "Authorization": f"Bearer {self._settings.groq_api_key or ''}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _MODEL,
            "voice": voice.provider_voice_id,
            "input": text,
            "response_format": "wav",
        }

        # A real, measured constraint (not documented by the vendor page, only
        # discovered by exceeding it live): Groq enforces 10 requests/minute
        # for this model and returns a `Retry-After` header. One bounded
        # retry — honoring that header, capped — absorbs a transient
        # minute-boundary hit without silently failing or, worse, falling
        # back to a different provider's voice for what is really just
        # rate-limit backpressure (Constitution VI).
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

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        # Not real incremental streaming (capabilities().streaming is False):
        # the full stitched WAV is produced first, then yielded as one chunk,
        # so this adapter is still a valid participant in the shared
        # stream-based orchestration path (services/tts_service.py).
        if not self._settings.has_groq():
            raise ProviderError(self.id, "auth", "Groq credentials not configured")

        segments = _chunk_text(request.text)
        try:
            async with httpx.AsyncClient(timeout=request.timeout_s) as client:
                blobs = [
                    await self._synthesize_segment(client, segment, request.voice)
                    for segment in segments
                ]
        except httpx.TimeoutException as exc:
            raise ProviderError(self.id, "timeout", "Groq request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(self.id, "unavailable", "Groq unreachable") from exc

        yield _concat_wav(blobs)

    async def synthesize(self, request: ProviderRequest) -> bytes:
        chunks = [c async for c in self.stream(request)]
        return b"".join(chunks)
