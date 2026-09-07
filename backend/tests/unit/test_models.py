"""Validation rules from data-model.md (FR-003, FR-042)."""

import pytest
from pydantic import ValidationError

from backend.app.models.tts import MAX_INPUT_CHARS, TTSRequest


def test_empty_text_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="")


def test_whitespace_only_text_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="   \n\t  ")


def test_over_length_text_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="أ" * (MAX_INPUT_CHARS + 1))


def test_valid_text_accepted():
    req = TTSRequest(text="مرحبا")
    assert req.text == "مرحبا"


def test_invalid_locale_format_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="مرحبا", locale="arabic")


def test_valid_locale_accepted():
    req = TTSRequest(text="مرحبا", locale="ar-SA")
    assert req.locale == "ar-SA"


def test_speaking_rate_bounds():
    with pytest.raises(ValidationError):
        TTSRequest(text="مرحبا", speaking_rate=3.0)
    assert TTSRequest(text="مرحبا", speaking_rate=1.5).speaking_rate == 1.5


def test_default_emotion_is_neutral():
    from backend.app.models.voice import EmotionStyle

    assert TTSRequest(text="مرحبا").emotion == EmotionStyle.NEUTRAL
