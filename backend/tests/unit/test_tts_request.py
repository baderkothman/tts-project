from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.models.tts import TTSRequest


def test_blank_text_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="   ")


def test_unknown_dialect_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="مرحبا", dialect_id="atlantis")


def test_speed_out_of_range_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="مرحبا", speed=10.0)


def test_defaults_are_sane():
    req = TTSRequest(text="مرحبا")
    assert req.mode == "voice_design"
    assert req.dialect_id == "msa"
    assert req.pitch == "moderate pitch"
    assert req.speed == 1.0
    assert req.quality == "high"


def test_text_over_hard_cap_rejected():
    with pytest.raises(ValidationError):
        TTSRequest(text="ا" * 2001)
