"""Real end-to-end pipeline tests: real diacritizer weights, real Kokoro
weights, real Lahgtna weights, real audio stitching. Opt-in only — see
test_live_model.py's module docstring for why.

Run explicitly with:
    RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

if not os.environ.get("RUN_MODEL_INTEGRATION_TESTS"):
    pytest.skip(
        "set RUN_MODEL_INTEGRATION_TESTS=1 to run the real-model integration test",
        allow_module_level=True,
    )

from backend.app.config import Settings
from backend.app.models.tts import TTSRequest
from backend.app.services import diacritizer, english_tts
from backend.app.services.inference import TTSEngine
from backend.app.services.speech_pipeline import SpeechPipeline


@pytest.fixture(scope="module")
def pipeline() -> SpeechPipeline:
    engine = TTSEngine(Settings())
    engine.load()
    diacritizer.load()
    english_tts.load()
    return SpeechPipeline(engine)


async def test_native_mode_mixed_arabic_english(pipeline: SpeechPipeline):
    request = TTSRequest(
        text="اليوم عندي meeting مع الـ development team وبعدها رح اشتغل على React وFastAPI.",
        dialect_id="saudi",
        gender="male",
        pipeline_mode="native",
        quality="fast",
    )
    result = await pipeline.synthesize(request, ref_audio_bytes=None)
    assert result.sample_rate > 0
    assert len(result.samples) > 0
    assert result.preview is not None
    assert any(s.language == "en" for s in result.preview.segments)


async def test_dual_model_mode_produces_stitched_audio(pipeline: SpeechPipeline):
    if english_tts.load_error():
        pytest.skip(f"Kokoro unavailable in this environment: {english_tts.load_error()}")
    request = TTSRequest(
        text="اليوم عندي meeting مهم جدا.",
        dialect_id="egyptian",
        gender="female",
        pipeline_mode="dual_model",
        quality="fast",
    )
    result = await pipeline.synthesize(request, ref_audio_bytes=None)
    assert len(result.samples) > 0
    assert not any("unavailable" in w.lower() for w in result.warnings)


async def test_transliteration_mode_produces_audio(pipeline: SpeechPipeline):
    request = TTSRequest(
        text="اشتغل على Vercel اليوم",
        dialect_id="msa",
        pipeline_mode="transliteration",
        quality="fast",
    )
    result = await pipeline.synthesize(request, ref_audio_bytes=None)
    assert len(result.samples) > 0
    assert "Vercel" not in result.preview.processed_text


async def test_diacritized_dialectal_text_generates(pipeline: SpeechPipeline):
    # "lebanese" used to be here — removed from the dialect catalogue for
    # not producing real dialect conditioning (see data/dialects.py); any
    # real remaining dialect exercises this test's actual point equally
    # well (diacritization on dialectal text), so swapped for "saudi".
    request = TTSRequest(
        text="شلونك اليوم؟",
        dialect_id="saudi",
        gender="male",
        quality="fast",
    )
    result = await pipeline.synthesize(request, ref_audio_bytes=None)
    assert len(result.samples) > 0
    ar_segment = result.preview.segments[0]
    assert ar_segment.diacritized is True
    assert ar_segment.speak_text != ar_segment.original_text
