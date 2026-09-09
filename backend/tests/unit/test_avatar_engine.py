"""Unit tests for the `EmotionConfig`/`AvatarEngine` abstraction layer
itself — no engine, no ffmpeg, no model."""

from __future__ import annotations

import pytest

from backend.app.data.emotions import EMOTION_NAMES
from backend.app.services.avatar_engine import AvatarEngineError, EmotionConfig


@pytest.mark.parametrize("name", EMOTION_NAMES)
def test_every_emotion_preset_builds_a_config_in_range(name):
    config = EmotionConfig.for_emotion(name)
    for field in ("expression_strength", "head_motion", "eye_motion", "smile"):
        value = getattr(config, field)
        assert 0.0 <= value <= 1.0, f"{name}.{field} = {value} out of 0..1"
    # blink_rate is a multiplier, not a 0..1 intensity — but should still be
    # "close to natural" per the brief's "constrained intensity, not
    # cartoon-like" requirement, not an arbitrary huge number.
    assert 0.0 < config.blink_rate <= 2.0


def test_emotion_configs_are_actually_distinct():
    # A real, meaningful check: presets shouldn't accidentally collapse to
    # the same tuple (e.g. a copy-paste of "neutral" for everything).
    configs = {name: EmotionConfig.for_emotion(name) for name in EMOTION_NAMES}
    assert len(set(configs.values())) == len(EMOTION_NAMES)


def test_no_preset_pushes_expression_past_the_brief_s_constrained_ceiling():
    # The brief this feature was built against is explicit that emotion
    # must use "constrained intensity rather than exaggerated cartoon-like
    # motion" — a real, checkable ceiling, not just a comment.
    for name in EMOTION_NAMES:
        assert EmotionConfig.for_emotion(name).expression_strength <= 0.6


def test_avatar_engine_error_carries_kind_and_message():
    err = AvatarEngineError("generation_failed", "boom")
    assert err.kind == "generation_failed"
    assert str(err) == "boom"
