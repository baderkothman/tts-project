"""Raw-vs-corrected comparison assembly tests (US7, T152)."""

from __future__ import annotations

import pytest

from backend.app.config import Settings
from backend.app.providers.registry import ProviderRegistry
from backend.app.services import dialect_service


@pytest.mark.asyncio
async def test_no_applicable_correction_yields_empty_changes_and_identical_audio():
    registry = ProviderRegistry(settings=Settings())
    result = await dialect_service.compare(
        "مرحبا كيف حالك اليوم",
        dialect=None,
        registry=registry,
        hf_token=None,
        timeout_s=10.0,
    )
    assert result.changes == []
    assert result.raw_audio_ref == result.corrected_audio_ref
    assert result.raw_audio_ref != ""


@pytest.mark.asyncio
async def test_dictionary_correction_is_reflected_in_changes_and_processed_text():
    registry = ProviderRegistry(settings=Settings())
    result = await dialect_service.compare(
        "بيروت مدينة جميلة",
        dialect=None,
        registry=registry,
        hf_token=None,
        timeout_s=10.0,
    )
    assert any("بيروت" in c for c in result.changes)
    assert "بَيْرُوت" in result.processed_text.processed


@pytest.mark.asyncio
async def test_architecture_used_is_from_fr054_vocabulary():
    registry = ProviderRegistry(settings=Settings())
    result = await dialect_service.compare(
        "مرحبا", dialect=None, registry=registry, hf_token=None, timeout_s=10.0
    )
    assert result.architecture_used in {"existing_tts", "hf_preprocessing_existing_tts", "hf_native_tts"}
