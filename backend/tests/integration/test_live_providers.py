"""Live provider tests (research R9). Skipped when credentials are absent —
never failed — so the default suite stays honest about what actually ran."""

import pytest

from backend.app.config import get_settings
from backend.app.providers.azure import AzureProvider
from backend.app.providers.base import ProviderRequest
from backend.app.providers.edge import EdgeProvider
from backend.app.providers.elevenlabs import ElevenLabsProvider
from backend.app.services.voice_router import resolve_voice

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_edge_live_synthesis_produces_audio():
    """Edge needs no credentials, but this still hits the live network
    endpoint, so it is kept in the integration tier rather than the default
    offline suite (which must never make live calls, Constitution VIII)."""
    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale="ar-SA")
    request = ProviderRequest(text="اختبار", voice=voice)
    audio = await provider.synthesize(request)
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_azure_live_synthesis_when_configured():
    settings = get_settings()
    if not settings.has_azure():
        pytest.skip("AZURE_SPEECH_KEY/AZURE_SPEECH_REGION not configured")
    provider = AzureProvider(settings=settings)
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale="ar-SA")
    request = ProviderRequest(text="اختبار", voice=voice)
    audio = await provider.synthesize(request)
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_elevenlabs_live_synthesis_when_configured():
    settings = get_settings()
    if not settings.has_elevenlabs():
        pytest.skip("ELEVENLABS_API_KEY not configured")
    provider = ElevenLabsProvider(settings=settings)
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices)
    request = ProviderRequest(text="اختبار", voice=voice)
    audio = await provider.synthesize(request)
    assert len(audio) > 0
