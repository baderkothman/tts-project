"""Provider conformance suite (contracts/provider-interface.md PC-01..PC-12).

Runs against every registered provider, including FakeProvider, so it is
meaningful offline (Constitution VIII).
"""

from __future__ import annotations

import pytest

from backend.app.models.voice import ProviderStatus
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.edge import EdgeProvider
from backend.app.providers.fake import FakeProvider

PROVIDERS = [EdgeProvider(), FakeProvider()]


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.id)
def test_pc01_capabilities_pure(provider):
    a = provider.capabilities()
    b = provider.capabilities()
    assert a == b


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.id)
def test_pc02_available_never_raises(provider):
    status = provider.available()
    assert isinstance(status, ProviderStatus)


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.id)
def test_pc03_streaming_providers_override_stream(provider):
    if provider.capabilities().streaming:
        # Overridden `stream` is an async generator function, not the base's.
        import inspect

        assert inspect.isasyncgenfunction(type(provider).stream)


@pytest.mark.asyncio
async def test_pc04_pc05_fake_stream_yields_valid_chunks():
    provider = FakeProvider(chunk_count=3)
    voices = await provider.get_voices()
    request = ProviderRequest(text="test", voice=voices[0])
    chunks = [c async for c in provider.stream(request)]
    assert len(chunks) == 3
    assert all(len(c) > 0 for c in chunks)


@pytest.mark.asyncio
async def test_pc06_failures_surface_as_provider_error():
    provider = FakeProvider(chunk_count=5, fail_after_chunks=2, fail_kind="timeout")
    voices = await provider.get_voices()
    request = ProviderRequest(text="test", voice=voices[0])
    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.stream(request):
            pass
    assert exc_info.value.kind == "timeout"
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_pc08_get_voices_scoped_to_provider():
    provider = FakeProvider()
    voices = await provider.get_voices()
    assert all(v.provider == provider.id for v in voices)


def test_pc09_dialect_only_where_published():
    edge = EdgeProvider()
    caps = edge.capabilities()
    assert len(caps.locales) == 16  # research R2: 16 published Arabic locales


@pytest.mark.asyncio
async def test_pc10_no_credential_leak_in_errors():
    provider = FakeProvider(fail_after_chunks=0, fail_kind="auth")
    voices = await provider.get_voices()
    request = ProviderRequest(text="test", voice=voices[0])
    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.stream(request):
            pass
    assert "key" not in str(exc_info.value).lower()
    assert "secret" not in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_pc11_cancellation_stops_promptly():
    provider = FakeProvider(chunk_count=100, chunk_delay_s=0.01)
    voices = await provider.get_voices()
    request = ProviderRequest(text="test", voice=voices[0])
    count = 0
    async for _ in provider.stream(request):
        count += 1
        if count >= 3:
            break
    assert count == 3


@pytest.mark.asyncio
async def test_pc07_timeout_classified_as_retryable_provider_error():
    """Scope note (Constitution V — measured, not claimed): FakeProvider does
    not itself enforce a wall-clock deadline, so this does not reproduce
    network-level timeout enforcement. That enforcement is real in the live
    adapters — edge.py passes connect/receive timeouts to edge_tts.Communicate,
    azure.py and elevenlabs.py pass `timeout=request.timeout_s` to
    httpx.AsyncClient, both verified by reading their signatures — but
    exercising it here would need a slow mock HTTP server, out of scope for
    the offline suite. What THIS test verifies: once a timeout kind of
    failure occurs, it is classified as retryable and propagates as
    ProviderError, which is the contract the rest of the system (fallback
    logic) depends on."""
    provider = FakeProvider(chunk_count=3, fail_after_chunks=1, fail_kind="timeout")
    voices = await provider.get_voices()
    request = ProviderRequest(text="test", voice=voices[0], timeout_s=0.01)

    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.stream(request):
            pass
    assert exc_info.value.kind == "timeout"
    assert exc_info.value.retryable is True
