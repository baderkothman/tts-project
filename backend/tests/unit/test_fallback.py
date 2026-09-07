"""Fallback on provider failure; service never crashes (FR-033, FR-034)."""

import pytest

from backend.app.models.tts import TTSRequest
from backend.app.providers.base import ProviderError
from backend.app.providers.fake import FakeProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.services.latency import LatencyTrace
from backend.app.services.tts_service import (
    NoProviderAvailableError,
    build_plan,
    stream_synthesis,
)


def _registry_with(primary: FakeProvider, fallback: FakeProvider) -> ProviderRegistry:
    reg = ProviderRegistry.__new__(ProviderRegistry)
    reg._settings = type("S", (), {"tts_default_provider": "fake", "tts_fallback_provider": "backup", "tts_request_timeout_s": 30.0})()
    reg._providers = {"fake": primary, "backup": fallback}
    return reg


@pytest.mark.asyncio
async def test_failure_before_any_byte_sent_triggers_fallback():
    """Fallback is safe here: the primary fails on its very first chunk, so
    nothing has reached the client yet."""
    primary = FakeProvider(chunk_count=5, fail_after_chunks=0, fail_kind="timeout")
    primary.id = "fake"
    fallback = FakeProvider(chunk_count=3)
    fallback.id = "backup"
    registry = _registry_with(primary, fallback)

    request = TTSRequest(text="مرحبا", provider="fake")
    trace = LatencyTrace()
    plan = await build_plan(registry, request, trace)

    chunks = [c async for c in stream_synthesis(registry, plan, trace)]
    assert len(chunks) == 3
    assert plan.used_fallback is True
    assert plan.fallback_reason is not None


@pytest.mark.asyncio
async def test_failure_after_bytes_sent_truncates_not_falls_back():
    """Once audio has reached the client, switching providers would produce
    corrupted mixed-voice output, so the stream truncates instead
    (contracts/http-api.md)."""
    primary = FakeProvider(chunk_count=5, fail_after_chunks=2, fail_kind="timeout")
    primary.id = "fake"
    fallback = FakeProvider(chunk_count=3)
    fallback.id = "backup"
    registry = _registry_with(primary, fallback)

    request = TTSRequest(text="مرحبا", provider="fake")
    trace = LatencyTrace()
    plan = await build_plan(registry, request, trace)

    chunks = []
    with pytest.raises(ProviderError):
        async for c in stream_synthesis(registry, plan, trace):
            chunks.append(c)
    assert len(chunks) == 2  # only the primary's pre-failure chunks
    assert plan.used_fallback is False


@pytest.mark.asyncio
async def test_no_provider_available_raises_actionable_error():
    registry = ProviderRegistry.__new__(ProviderRegistry)
    registry._settings = type("S", (), {"tts_default_provider": "nope", "tts_request_timeout_s": 30.0})()
    registry._providers = {}

    request = TTSRequest(text="مرحبا")
    trace = LatencyTrace()
    with pytest.raises(NoProviderAvailableError):
        await build_plan(registry, request, trace)
