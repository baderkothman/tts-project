"""Abandoning the stream stops provider consumption promptly (PC-11)."""

import pytest

from backend.app.providers.base import ProviderRequest
from backend.app.providers.fake import FakeProvider


@pytest.mark.asyncio
async def test_breaking_out_of_stream_stops_consumption():
    provider = FakeProvider(chunk_count=1000, chunk_delay_s=0.001)
    voices = await provider.get_voices()
    request = ProviderRequest(text="x", voice=voices[0])

    count = 0
    async for _ in provider.stream(request):
        count += 1
        if count >= 5:
            break

    assert count == 5  # did not run to 1000
