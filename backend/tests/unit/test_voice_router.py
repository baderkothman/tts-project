"""Voice router resolution (FR-025a, FR-026, AC-03, AC-04)."""

import pytest

from backend.app.models.voice import Dialect
from backend.app.providers.edge import EdgeProvider
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
        resolve_voice(provider, voices, voice_id="azure:ar-SA-female")
