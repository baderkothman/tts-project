"""Dialect resolution and fallback-routing tests (FR-048, FR-051, FR-057,
SC-019, T141).
"""

from __future__ import annotations

import pytest

from backend.app.config import Settings
from backend.app.providers.registry import ProviderRegistry
from backend.app.services import dialect_service


@pytest.mark.asyncio
async def test_user_selection_overrides_classifier():
    # No HF_TOKEN configured -> classifier can't run either way, but the
    # selection must still win and be reported as user_selected (AC-11).
    result = await dialect_service.resolve("شو رأيك", dialect="lebanese", hf_token=None)
    assert result.resolved_dialect == "lebanese"
    assert result.source == "user_selected"


@pytest.mark.asyncio
async def test_classifier_used_when_no_selection_and_degrades_honestly():
    # No HF_TOKEN -> classifier can't run -> honest msa fallback with a
    # stated reason, never a silent/invented dialect (FR-057).
    result = await dialect_service.resolve("شو رأيك", dialect=None, hf_token=None)
    assert result.source == "classifier"
    assert result.resolved_dialect == "msa"
    assert result.unavailable_reason is not None


@pytest.mark.asyncio
async def test_select_voice_falls_back_to_existing_provider_when_hf_unavailable():
    # huggingface provider has no HF_TOKEN configured in this registry, so
    # it must report unavailable and the dialect still gets an existing
    # provider's voice (FR-057, SC-019) rather than raising.
    registry = ProviderRegistry(settings=Settings(hf_token=None))
    provider, voice, architecture = await dialect_service.select_voice_for_dialect("egyptian", registry)
    assert provider.id != "huggingface"
    assert architecture == "existing_tts"
    assert voice.provider == provider.id


@pytest.mark.asyncio
async def test_select_voice_unknown_dialect_falls_back_to_msa_profile():
    registry = ProviderRegistry(settings=Settings())
    provider, voice, architecture = await dialect_service.select_voice_for_dialect("maghrebi", registry)
    # "maghrebi" has no DialectProfile (spec.md's minimum six don't include
    # it) — must still resolve to *something* servable, not raise.
    assert provider is not None
    assert voice is not None
