"""Edge adapter tests (US1). Real live calls are exercised in
tests/integration; these are structural/offline checks."""

import pytest

from backend.app.models.voice import ProviderStatus
from backend.app.providers.edge import EdgeProvider


def test_edge_capabilities_declare_streaming():
    caps = EdgeProvider().capabilities()
    assert caps.streaming is True
    assert caps.requires_credentials is False
    assert caps.native_emotions is False  # research R2


def test_edge_always_available_no_credentials():
    assert EdgeProvider().available() == ProviderStatus.AVAILABLE


@pytest.mark.asyncio
async def test_edge_get_voices_returns_16_locales():
    voices = await EdgeProvider().get_voices()
    assert len({v.locale for v in voices}) == 16
    assert len(voices) == 32
