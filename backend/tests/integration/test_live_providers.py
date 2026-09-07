"""Live provider tests (research R9). Skipped when credentials are absent —
never failed — so the default suite stays honest about what actually ran."""

import pytest

from backend.app.config import get_settings
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.edge import EdgeProvider
from backend.app.providers.elevenlabs import ElevenLabsProvider
from backend.app.providers.groq import GroqProvider
from backend.app.providers.huggingface.provider import HuggingFaceProvider
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
async def test_groq_live_synthesis_when_configured():
    settings = get_settings()
    if not settings.has_groq():
        pytest.skip("GROQ_API_KEY not configured")
    provider = GroqProvider(settings=settings)
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
    try:
        audio = await provider.synthesize(request)
    except ProviderError as exc:
        # A configured, valid key that the current plan still can't use for
        # this voice (docs/TTS_EVALUATION.md) is a known, live-confirmed
        # account restriction, not a code defect — skip with the reason
        # rather than fail, matching the "skip what genuinely can't run
        # here, fail what's actually broken" principle this suite already
        # applies to missing credentials (research R9). Any OTHER
        # ProviderError kind (auth, server, ...) still fails loudly: that
        # would mean something actually regressed.
        if exc.kind == "payment_required":
            pytest.skip(f"ElevenLabs account restriction, not a code defect: {exc.message}")
        raise
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_huggingface_live_synthesis_when_configured():
    """Quickstart V15's automated counterpart (T159/T160): the one enabled
    dialect_tts registry entry, called live, skipped honestly when HF_TOKEN
    is absent.

    Live-discovered (2026-09-07, once a real HF_TOKEN with the
    `inference.serverless.write` permission was configured): Hugging Face's
    Inference Providers system returns 400 "Model not supported by provider
    hf-inference" for `oddadmix/chatterbox-egyptian-v0` — confirmed via the
    model's own `inference: null` metadata on `huggingface.co/api/models/...`
    — a real platform constraint (this niche community model is not deployed
    on any Inference Provider), not a token or code defect. Skipped for that
    specific, confirmed reason, matching the "skip what genuinely can't run
    here, fail what's actually broken" principle already applied to
    ElevenLabs' payment_required case."""
    settings = get_settings()
    if not settings.has_huggingface():
        pytest.skip("HF_TOKEN not configured")
    provider = HuggingFaceProvider(settings=settings)
    voices = await provider.get_voices()
    if not voices:
        pytest.skip("no enabled Hugging Face dialect_tts model in the registry")
    request = ProviderRequest(text="إزيك؟ عامل إيه؟", voice=voices[0])
    try:
        audio = await provider.synthesize(request)
    except ProviderError as exc:
        if exc.kind == "bad_request" and "not supported by provider" in exc.message.lower():
            pytest.skip(f"Model not deployed on any HF Inference Provider, not a code defect: {exc.message}")
        raise
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_huggingface_dialect_classifier_live_when_configured():
    """Live-discovered (2026-09-07): the same class of finding as the TTS
    test above — Hugging Face returns 410 Gone for
    `IbrahimAmin/marbertv2-arabic-written-dialect-classifier` via
    hf-inference ("the requested model is deprecated and no longer
    supported by provider hf-inference"), independent of token permissions
    (confirmed live after granting `inference.serverless.write`)."""
    from backend.app.text_processing.huggingface.dialect_classifier import classify

    settings = get_settings()
    if not settings.has_huggingface():
        pytest.skip("HF_TOKEN not configured")
    result = await classify("شو رأيك نطلع نشرب قهوة بعد الشغل؟", hf_token=settings.hf_token)
    if result.label is None and result.unavailable_reason and "410" in result.unavailable_reason:
        pytest.skip(f"Model not served by hf-inference (410 Gone), not a code defect: {result.unavailable_reason}")
    assert result.label is not None, result.unavailable_reason
