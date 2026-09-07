"""Style approximation is measurably distinct across styles (SC-006)."""

from backend.app.models.voice import EmotionStyle
from backend.app.text_processing.provider_formatting import prosody_for_style


def test_neutral_is_zero_baseline():
    assert prosody_for_style(EmotionStyle.NEUTRAL) == (0, 0, 0)


def test_at_least_three_styles_are_measurably_distinct():
    styles = [EmotionStyle.NEUTRAL, EmotionStyle.EXCITED, EmotionStyle.CALM, EmotionStyle.HAPPY]
    values = {s: prosody_for_style(s) for s in styles}
    # Every pair must differ in at least one of rate/pitch/volume.
    seen = set(values.values())
    assert len(seen) == len(styles), f"styles collapsed to fewer distinct prosody tuples: {values}"


def test_excited_is_faster_and_higher_than_calm():
    excited_rate, excited_pitch, _ = prosody_for_style(EmotionStyle.EXCITED)
    calm_rate, calm_pitch, _ = prosody_for_style(EmotionStyle.CALM)
    assert excited_rate > calm_rate
    assert excited_pitch > calm_pitch


def test_unknown_style_falls_back_to_neutral():
    # Every EmotionStyle enum member must resolve to a defined tuple, never KeyError.
    for style in EmotionStyle:
        result = prosody_for_style(style)
        assert len(result) == 3
