"""The Talking Avatar feature's emotion vocabulary.

Unlike `voice_design.py` (whose `Gender`/`Pitch` options are read directly
out of an installed model's own closed instruct vocabulary), there is no
single underlying avatar model yet to read a vocabulary from — see
`docs/AVATAR_MODEL_EVALUATION.md` for why. These six presets are therefore
this app's own normalized, model-agnostic representation (`EmotionConfig`,
defined in `services/avatar_engine.py`), designed to be mapped onto
whichever `AvatarEngine` is active rather than any one engine's own control
scheme. `EmotionName` is deliberately a closed set (like `Gender`/`Pitch`)
so the API and frontend never need to know an engine-specific string.

Intensities are kept modest on purpose — the brief this feature was built
against is explicit that emotion must never break lip sync and should read
as "constrained," not "exaggerated cartoon-like motion." `expression_strength`
tops out at 0.6 (excited) precisely so no preset asks an engine to push
facial deformation hard enough to plausibly fight the mouth-region motion
lip sync depends on.
"""

from __future__ import annotations

from typing import Literal

EmotionName = Literal["neutral", "happy", "sad", "excited", "calm", "professional"]

EMOTION_NAMES: list[EmotionName] = ["neutral", "happy", "sad", "excited", "calm", "professional"]

DEFAULT_EMOTION: EmotionName = "neutral"

# (expression_strength, head_motion, blink_rate, eye_motion, smile) — see
# `EmotionConfig` for what each field means and its valid range. `blink_rate`
# is a multiplier on a natural baseline (1.0 = unchanged), everything else is
# 0..1. Kept as plain tuples here (not `EmotionConfig` instances) so this
# data module has no import dependency on the services layer — `avatar_engine.py`
# builds the real `EmotionConfig` objects from this table at import time.
EMOTION_PRESET_VALUES: dict[EmotionName, tuple[float, float, float, float, float]] = {
    #                          expr  head  blink eye   smile
    "neutral": (0.15, 0.10, 1.0, 0.10, 0.05),
    "happy": (0.40, 0.25, 1.1, 0.20, 0.55),
    "sad": (0.30, 0.08, 0.7, 0.10, 0.0),
    # The one preset allowed above 0.5 expression_strength — still well
    # short of 1.0, and blink_rate stays close to natural (1.2, not 2x+)
    # specifically so "excited" doesn't read as manic.
    "excited": (0.60, 0.45, 1.3, 0.35, 0.45),
    "calm": (0.12, 0.05, 0.8, 0.08, 0.15),
    "professional": (0.18, 0.12, 1.0, 0.12, 0.10),
}
