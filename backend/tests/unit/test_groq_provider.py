"""Groq adapter tests (offline, mocked). T016."""

from __future__ import annotations

import httpx
import pytest

from backend.app.data.voices import GROQ_VOICES
from backend.app.providers.base import ProviderError
from backend.app.providers.groq import GroqProvider, _chunk_text, _concat_wav

_RealAsyncClient = httpx.AsyncClient


def _patch_client(monkeypatch, handler) -> None:
    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("backend.app.providers.groq.httpx.AsyncClient", factory)


def test_chunk_text_never_splits_mid_word():
    text = "و" * 190 + " " + "ب" * 50
    segments = _chunk_text(text, limit=200)
    assert all(len(s) <= 200 for s in segments)
    assert "".join(segments).replace(" ", "") == text.replace(" ", "")


def test_concat_wav_produces_valid_wav():
    import io
    import wave

    def make_wav(n_frames: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00" * n_frames)
        return buf.getvalue()

    combined = _concat_wav([make_wav(100), make_wav(200)])
    with wave.open(io.BytesIO(combined), "rb") as w:
        assert w.getnframes() == 300


def test_available_reflects_api_key():
    assert GroqProvider(api_key=None).available() is False
    assert GroqProvider(api_key="fake").available() is True


@pytest.mark.asyncio
async def test_401_maps_to_auth(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    _patch_client(monkeypatch, handler)
    provider = GroqProvider(api_key="fake")
    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize("مرحبا", GROQ_VOICES[0], timeout_s=5.0)
    assert exc_info.value.kind == "auth"
    assert "fake" not in exc_info.value.message


@pytest.mark.asyncio
async def test_429_retries_once_then_succeeds(monkeypatch):
    import wave
    import io

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0.01"})
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00" * 100)
        return httpx.Response(200, content=buf.getvalue())

    _patch_client(monkeypatch, handler)
    provider = GroqProvider(api_key="fake")
    audio = await provider.synthesize("مرحبا", GROQ_VOICES[0], timeout_s=5.0)
    assert len(audio) > 0
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_429_twice_raises_rate_limit(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "0.01"})

    _patch_client(monkeypatch, handler)
    provider = GroqProvider(api_key="fake")
    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize("مرحبا", GROQ_VOICES[0], timeout_s=5.0)
    assert exc_info.value.kind == "rate_limit"
