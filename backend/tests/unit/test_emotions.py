"""Sanity checks on the emotion preset table itself — separate from
`test_avatar_engine.py`'s checks on the `EmotionConfig` values those
presets produce."""

from __future__ import annotations

from backend.app.data.emotions import DEFAULT_EMOTION, EMOTION_NAMES, EMOTION_PRESET_VALUES


def test_every_emotion_name_has_a_preset():
    assert set(EMOTION_PRESET_VALUES.keys()) == set(EMOTION_NAMES)


def test_default_emotion_is_a_valid_name():
    assert DEFAULT_EMOTION in EMOTION_NAMES


def test_default_emotion_is_neutral():
    # Not an arbitrary choice — a generation with no emotion specified
    # should read as genuinely neutral, not implicitly "happy" or "excited".
    assert DEFAULT_EMOTION == "neutral"
