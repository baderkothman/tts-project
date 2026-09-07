"""Hugging Face provider adapter tests (FR-060, T133).

Mocks `InferenceClient` rather than hitting the network — the equivalent of
`httpx.MockTransport` for `test_groq_provider.py`/`test_elevenlabs_provider.py`,
adapted to the one adapter that uses the vendor's own SDK client (confined to
`providers/huggingface/inference_api.py`, per Constitution II).
"""

from __future__ import annotations

import pytest
from huggingface_hub.errors import HfHubHTTPError

from backend.app.config import Settings
from backend.app.models.voice import ProviderStatus
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.huggingface.provider import HuggingFaceProvider


def _settings(token: str | None = "fake-token") -> Settings:
    return Settings(hf_token=token)


def test_available_reflects_settings():
    assert HuggingFaceProvider(settings=_settings(None)).available() == ProviderStatus.MISSING_CREDENTIALS
    assert HuggingFaceProvider(settings=_settings()).available() == ProviderStatus.AVAILABLE


def test_capabilities_is_pure_and_stable():
    provider = HuggingFaceProvider(settings=_settings())
    assert provider.capabilities() == provider.capabilities()


@pytest.mark.asyncio
async def test_get_voices_only_includes_enabled_registry_entries():
    provider = HuggingFaceProvider(settings=_settings())
    voices = await provider.get_voices()
    assert all(v.provider == "huggingface" for v in voices)
    # egyptian-tts-chatterbox is the one enabled dialect_tts entry (T121)
    assert any(v.provider_voice_id == "oddadmix/chatterbox-egyptian-v0" for v in voices)


@pytest.mark.asyncio
async def test_voices_have_honest_unknown_gender():
    # FR-059: no gender metadata is documented on any cleared dialect_tts
    # candidate — must be labeled "unknown", never guessed.
    provider = HuggingFaceProvider(settings=_settings())
    voices = await provider.get_voices()
    assert voices and all(v.gender == "unknown" for v in voices)


@pytest.mark.asyncio
async def test_synthesize_without_token_raises_auth_error():
    provider = HuggingFaceProvider(settings=_settings(None))
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize(request)
    assert exc_info.value.kind == "auth"


@pytest.mark.asyncio
async def test_synthesize_maps_401_to_auth(monkeypatch):
    import httpx

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def text_to_speech(self, text, **kwargs):
            resp = httpx.Response(401, request=httpx.Request("POST", "https://example.test"))
            raise HfHubHTTPError("unauthorized", response=resp)

    monkeypatch.setattr("backend.app.providers.huggingface.inference_api.InferenceClient", _FakeClient)

    provider = HuggingFaceProvider(settings=_settings())
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize(request)
    assert exc_info.value.kind == "auth"
    assert "fake-token" not in exc_info.value.message  # PC-10: no credential leak


@pytest.mark.asyncio
async def test_synthesize_maps_503_to_timeout_cold_start(monkeypatch):
    import httpx

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def text_to_speech(self, text, **kwargs):
            resp = httpx.Response(503, request=httpx.Request("POST", "https://example.test"))
            raise HfHubHTTPError("loading", response=resp)

    monkeypatch.setattr("backend.app.providers.huggingface.inference_api.InferenceClient", _FakeClient)

    provider = HuggingFaceProvider(settings=_settings())
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    with pytest.raises(ProviderError) as exc_info:
        await provider.synthesize(request)
    assert exc_info.value.kind == "timeout"
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_successful_synthesis_returns_audio(monkeypatch):
    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def text_to_speech(self, text, **kwargs):
            return b"\x00\x01" * 50

    monkeypatch.setattr("backend.app.providers.huggingface.inference_api.InferenceClient", _FakeClient)

    provider = HuggingFaceProvider(settings=_settings())
    voices = await provider.get_voices()
    request = ProviderRequest(text="اختبار", voice=voices[0])

    audio = await provider.synthesize(request)
    assert len(audio) == 100
