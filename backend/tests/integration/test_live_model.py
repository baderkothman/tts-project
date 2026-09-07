"""One real end-to-end call through the actual `oddadmix/lahgtna-omnivoice-v2`
weights. Loads real weights (2.4GB, downloaded on first run) and runs on
whatever device this machine has — opt-in only, since it takes real time and
is not something a default `pytest` run should pay for.

Run explicitly with:
    RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
"""

from __future__ import annotations

import os

import pytest

from backend.app.config import Settings
from backend.app.models.tts import TTSRequest
from backend.app.services.inference import TTSEngine

pytestmark = pytest.mark.integration

if not os.environ.get("RUN_MODEL_INTEGRATION_TESTS"):
    pytest.skip(
        "set RUN_MODEL_INTEGRATION_TESTS=1 to run the real-model integration test",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def engine() -> TTSEngine:
    e = TTSEngine(Settings())
    e.load()
    return e


async def test_voice_design_generates_real_audio(engine: TTSEngine):
    request = TTSRequest(text="مرحبا، كيف حالك اليوم؟", dialect_id="saudi", gender="female")
    result = await engine.generate(request, ref_audio_bytes=None)
    assert result.sample_rate == 24000
    assert len(result.samples) > 0


async def test_every_dialect_with_a_language_code_does_not_error(engine: TTSEngine):
    from backend.app.data.dialects import DIALECTS

    for dialect in DIALECTS:
        request = TTSRequest(text="أهلاً وسهلاً بكم", dialect_id=dialect.id, gender="male", quality="fast")
        result = await engine.generate(request, ref_audio_bytes=None)
        assert len(result.samples) > 0
