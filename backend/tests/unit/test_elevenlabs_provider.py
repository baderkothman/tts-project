"""ElevenLabs adapter tests (US1). Real live calls are exercised in
tests/integration; these are structural/offline checks against a mocked
transport, so they run without a key and without hitting the network.
"""

from __future__ import annotations

import httpx
import pytest

from backend.app.config import Settings
from backend.app.models.voice import ProviderStatus
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.elevenlabs import ElevenLabsProvider

# Captured before any monkeypatching, since `elevenlabs.py`'s `httpx` is the
# same module object this test file imports — patching `httpx.AsyncClient`
# by name and then calling `httpx.AsyncClient(...)` from inside the patch
# would recurse into itself.
_RealAsyncClient = httpx.AsyncClient


def _patch_client(monkeypatch, handler) -> None:
    """Force ElevenLabsProvider.stream()'s internally constructed
    httpx.AsyncClient onto a MockTransport, dropping the `timeout` kwarg it
    is normally called with (MockTransport doesn't need one)."""

    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("backend.app.providers.elevenlabs.httpx.AsyncClient", factory)


def test_capabilities_declare_no_arabic_locale():
    caps = ElevenLabsProvider(settings=Settings(elevenlabs_api_key="fake")).capabilities()
    assert caps.locales == []  # FR-027: no documented Arabic locale codes
    assert caps.phoneme is False  # phoneme tags are English-only (research R4)


def test_available_reflects_settings():
    assert ElevenLabsProvider(settings=Settings(elevenlabs_api_key=None)).available() == (
        ProviderStatus.MISSING_CREDENTIALS
    )
    assert ElevenLabsProvider(settings=Settings(elevenlabs_api_key="fake")).available() == (
        ProviderStatus.AVAILABLE
    )


@pytest.mark.asyncio
async def test_402_maps_to_payment_required_not_bad_request(monkeypatch):
    """Regression: live-discovered — the free tier rejects API calls to
    public "library" voices with 402, distinct from a malformed request
    (400) or an invalid key (401). Caught by a real live call once a key was
    configured; this test locks the mapping in place offline."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={"detail": {"code": "paid_plan_required", "message": "upgrade required"}},
        )

    _patch_client(monkeypatch, handler)

    provider = ElevenLabsProvider(settings=Settings(elevenlabs_api_key="fake"))
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize(request)

    assert exc_info.value.kind == "payment_required"
    assert exc_info.value.retryable is False  # paying doesn't happen by retrying
    assert "fake" not in exc_info.value.message  # no credential leak (PC-10)


@pytest.mark.asyncio
async def test_402_is_distinguishable_from_401(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid key"})

    _patch_client(monkeypatch, handler)

    provider = ElevenLabsProvider(settings=Settings(elevenlabs_api_key="fake"))
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize(request)

    assert exc_info.value.kind == "auth"


@pytest.mark.asyncio
async def test_successful_synthesis_returns_audio(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"\x00\x01" * 100)

    _patch_client(monkeypatch, handler)

    provider = ElevenLabsProvider(settings=Settings(elevenlabs_api_key="fake"))
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    audio = await provider.synthesize(request)
    assert len(audio) == 200
