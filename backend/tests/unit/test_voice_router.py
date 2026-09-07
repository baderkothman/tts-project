"""Voice router resolution (FR-025a, FR-026, AC-03, AC-04)."""

import pytest

from backend.app.config import Settings
from backend.app.models.voice import Dialect
from backend.app.providers.edge import EdgeProvider
from backend.app.providers.groq import GroqProvider
from backend.app.services.voice_router import VoiceResolutionError, resolve_voice


@pytest.mark.asyncio
@pytest.mark.parametrize("dialect", list(Dialect))
async def test_resolve_by_dialect_family(dialect):
    from backend.app.data.voices import locales_for_dialect

    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, dialect=dialect)
    assert voice.locale in locales_for_dialect(dialect)


@pytest.mark.asyncio
async def test_resolve_by_explicit_locale():
    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale="ar-MA")
    assert voice.locale == "ar-MA"


@pytest.mark.asyncio
async def test_unsupported_locale_raises_with_alternatives():
    provider = EdgeProvider()
    voices = await provider.get_voices()
    with pytest.raises(VoiceResolutionError) as exc_info:
        resolve_voice(provider, voices, locale="fr-FR")
    assert len(exc_info.value.valid_alternatives) == 16


@pytest.mark.asyncio
async def test_no_selection_defaults_to_msa():
    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices)
    assert voice.locale == "ar-SA"


@pytest.mark.asyncio
async def test_voice_id_not_on_provider_raises():
    provider = EdgeProvider()
    voices = await provider.get_voices()
    with pytest.raises(VoiceResolutionError):
        resolve_voice(provider, voices, voice_id="groq:ar-SA-female")


@pytest.mark.asyncio
async def test_dialect_resolution_keys_on_voice_dialect_not_locale_string():
    """Regression: Groq's Saudi-dialect voices and Edge's MSA-trained voices
    share the locale string "ar-SA" but carry different `dialect` values
    (research: docs/DIALECT_EVALUATION.md). A locale-string-based dialect
    lookup (the original implementation) resolved Gulf-family requests against
    Edge's locale table regardless of which provider was asked, so a Gulf
    request routed to Groq raised VoiceResolutionError even though Groq
    serves nothing but Gulf-dialect voices. Caught by exercising Groq
    directly rather than only ever testing dialect resolution against Edge."""
    provider = GroqProvider(settings=Settings(groq_api_key="fake"))
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, dialect=Dialect.GULF)
    assert voice.provider == "groq"
    assert voice.dialect == Dialect.GULF

    with pytest.raises(VoiceResolutionError):
        resolve_voice(provider, voices, dialect=Dialect.EGYPTIAN)
