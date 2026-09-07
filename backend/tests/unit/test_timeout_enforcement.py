"""Every provider call carries an explicit, configured timeout (FR-032, PC-07).

Regression test for a real gap caught during implementation: the Edge
adapter originally ignored request.timeout_s entirely, and build_plan never
populated it from settings, so the configured timeout was silently unused.
"""

import pytest

from backend.app.config import Settings
from backend.app.models.tts import TTSRequest
from backend.app.providers.fake import FakeProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.services.latency import LatencyTrace
from backend.app.services.tts_service import build_plan


@pytest.mark.asyncio
async def test_build_plan_populates_timeout_from_settings():
    registry = ProviderRegistry.__new__(ProviderRegistry)
    registry._settings = Settings(tts_request_timeout_s=7.5, tts_default_provider="fake")
    registry._providers = {"fake": FakeProvider()}

    request = TTSRequest(text="مرحبا", provider="fake")
    trace = LatencyTrace()
    plan = await build_plan(registry, request, trace)

    assert plan.provider_request.timeout_s == 7.5
