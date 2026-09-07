"""FR-005, T015."""

from __future__ import annotations

import pytest

from backend.app.providers.fake import FAKE_VOICES
from backend.app.services.voice_resolution import VoiceResolutionError, resolve_voice


def test_explicit_voice_id_wins():
    v = resolve_voice(FAKE_VOICES, voice_id="fake:female-1")
    assert v.id == "fake:female-1"


def test_gender_resolves_to_a_default():
    v = resolve_voice(FAKE_VOICES, gender="male")
    assert v.gender == "male"


def test_unknown_voice_id_raises_with_alternatives():
    with pytest.raises(VoiceResolutionError) as exc_info:
        resolve_voice(FAKE_VOICES, voice_id="not-a-real-voice")
    assert "fake:male-1" in exc_info.value.valid_alternatives


def test_no_selection_returns_first_voice():
    v = resolve_voice(FAKE_VOICES)
    assert v == FAKE_VOICES[0]
