"""First chunk arrives before the stream completes (AC-07, SC-002)."""

import pytest

from backend.app.providers.base import ProviderRequest
from backend.app.providers.fake import FakeProvider
from backend.app.services.latency import LatencyTrace
from backend.app.services.tts_service import SynthesisPlan, stream_synthesis
from backend.app.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_first_chunk_not_accumulated(monkeypatch):
    provider = FakeProvider(chunk_count=5, chunk_delay_s=0.01)
    voices = await provider.get_voices()
    plan = SynthesisPlan(
        provider=provider,
        voice=voices[0],
        processed=__import__(
            "backend.app.models.tts", fromlist=["ProcessedText"]
        ).ProcessedText(original="x", processed="x"),
        provider_request=ProviderRequest(text="x", voice=voices[0]),
        emotion_native=False,
    )
    trace = LatencyTrace()
    registry = ProviderRegistry.__new__(ProviderRegistry)  # unused fallback path

    seen = []
    async for chunk in stream_synthesis(registry, plan, trace):
        seen.append(chunk)
        if len(seen) == 1:
            # T4 (first provider byte) must be marked before all 5 chunks arrive.
            assert trace.has("T4")
    assert len(seen) == 5
