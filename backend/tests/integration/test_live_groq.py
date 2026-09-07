"""Live Groq calls — skipped, not failed, when GROQ_API_KEY is absent (T022)."""

from __future__ import annotations

import pytest

from backend.app.config import get_settings
from backend.app.data.voices import GROQ_VOICES
from backend.app.providers.groq import GroqProvider

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_male_and_female_voice_live():
    settings = get_settings()
    if not settings.has_groq():
        pytest.skip("GROQ_API_KEY not configured")

    provider = GroqProvider(api_key=settings.groq_api_key)
    male_voice = next(v for v in GROQ_VOICES if v.gender == "male")
    female_voice = next(v for v in GROQ_VOICES if v.gender == "female")

    male_audio = await provider.synthesize("وش رايك نطلع نتعشى اليوم؟", male_voice, timeout_s=30.0)
    female_audio = await provider.synthesize("وش رايك نطلع نتعشى اليوم؟", female_voice, timeout_s=30.0)

    assert len(male_audio) > 0
    assert len(female_audio) > 0
