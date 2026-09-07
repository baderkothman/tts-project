"""Groq adapter: 200-char chunking and WAV stitching (research R1).

These are new mechanics this adapter alone needs (no other provider in the
catalogue has a sub-request character cap), so they get dedicated tests
rather than relying on the shared provider-conformance suite.
"""

from __future__ import annotations

import io
import wave

import httpx
import pytest

from backend.app.config import Settings
from backend.app.models.voice import ProviderStatus
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.groq import GroqProvider, _chunk_text, _concat_wav


def test_chunk_text_respects_limit():
    text = "مرحبا " * 100  # far over 200 chars
    segments = _chunk_text(text, limit=200)
    assert all(len(s) <= 200 for s in segments)
    assert len(segments) > 1


def test_chunk_text_never_splits_a_word():
    text = "اليوم عندي meeting مع فريق الـ AI الساعة 3 PM " * 5
    segments = _chunk_text(text, limit=50)
    # Every word from the original text must reappear whole in some segment.
    original_words = text.split()
    rejoined_words = " ".join(segments).split()
    assert rejoined_words == original_words


def test_chunk_text_short_input_is_single_segment():
    segments = _chunk_text("مرحبا بالعالم")
    assert segments == ["مرحبا بالعالم"]


def test_chunk_text_empty_input_returns_one_empty_segment():
    assert _chunk_text("") == [""]


def _make_wav(frames: bytes, *, nchannels=1, sampwidth=2, framerate=24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(frames)
    return buf.getvalue()


def test_concat_wav_single_blob_passthrough():
    blob = _make_wav(b"\x00\x01" * 10)
    assert _concat_wav([blob]) == blob


def test_concat_wav_merges_frames_into_one_valid_wav():
    blob_a = _make_wav(b"\x00\x01" * 10)
    blob_b = _make_wav(b"\x02\x03" * 5)
    merged = _concat_wav([blob_a, blob_b])

    with wave.open(io.BytesIO(merged), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000
        assert w.getnframes() == 15  # 10 frames + 5 frames
        assert w.readframes(15) == (b"\x00\x01" * 10) + (b"\x02\x03" * 5)


def test_capabilities_report_saudi_dialect_not_streaming():
    provider = GroqProvider(settings=Settings(groq_api_key="fake"))
    caps = provider.capabilities()
    assert caps.streaming is False
    assert caps.locales == ["ar-SA"]
    assert caps.requires_credentials is True


@pytest.mark.asyncio
async def test_stream_without_credentials_raises_auth_error():
    provider = GroqProvider(settings=Settings(groq_api_key=None))
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])
    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.stream(request):
            pass
    assert exc_info.value.kind == "auth"


@pytest.mark.asyncio
async def test_get_voices_are_gulf_dialect_and_scoped_to_provider():
    provider = GroqProvider(settings=Settings(groq_api_key="fake"))
    voices = await provider.get_voices()
    assert len(voices) == 6
    assert all(v.provider == "groq" for v in voices)
    assert all(v.dialect == "gulf" for v in voices)
    assert {v.gender for v in voices} == {"male", "female"}


@pytest.mark.asyncio
async def test_rate_limit_retries_once_then_succeeds(monkeypatch):
    """Regression: live-discovered 10 req/min limit on this model (not in the
    vendor docs fetched during research). A single Retry-After-honoring
    retry should absorb one 429 rather than failing or falling back
    immediately."""
    sleeps: list[float] = []
    monkeypatch.setattr(
        "backend.app.providers.groq.asyncio.sleep",
        lambda s: sleeps.append(s) or _noop_coro(),
    )

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, json={"error": "rate limited"})
        return httpx.Response(200, content=_make_wav(b"\x00\x01" * 5))

    provider = GroqProvider(settings=Settings(groq_api_key="fake"))
    voices = await provider.get_voices()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        audio = await provider._synthesize_segment(client, "اختبار", voices[0])

    assert calls["n"] == 2
    assert sleeps == [2.0]
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_rate_limit_twice_raises_retryable_error(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.groq.asyncio.sleep", lambda s: _noop_coro()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "1"}, json={"error": "rate limited"})

    provider = GroqProvider(settings=Settings(groq_api_key="fake"))
    voices = await provider.get_voices()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError) as exc_info:
            await provider._synthesize_segment(client, "اختبار", voices[0])

    assert exc_info.value.kind == "rate_limit"
    assert exc_info.value.retryable is True


async def _noop_coro():
    return None


def test_available_reflects_settings():
    assert GroqProvider(settings=Settings(groq_api_key=None)).available() == (
        ProviderStatus.MISSING_CREDENTIALS
    )
    assert GroqProvider(settings=Settings(groq_api_key="fake")).available() == (
        ProviderStatus.AVAILABLE
    )
