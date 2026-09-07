"""Voice-design attribute options this app exposes.

These are not invented — they are the exact, closed enum the installed
`omnivoice` package validates an `instruct` string against
(`omnivoice.utils.voice_design._INSTRUCT_CATEGORIES`, confirmed by reading
the installed package source: passing anything outside this set raises
`ValueError` from `OmniVoice.generate()`). Only the English-language
categories are relevant here — the package's Chinese-dialect category
(Mandarin topolects) and English-accent category are foreign to an Arabic
TTS product and are intentionally not exposed.

Dialect is deliberately NOT an instruct attribute — see
`backend/app/data/dialects.py` for why it is a `language` parameter
instead.
"""

from __future__ import annotations

from typing import Literal

Gender = Literal["male", "female"]
Pitch = Literal["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"]
AgeGroup = Literal["child", "teenager", "young adult", "middle-aged", "elderly"]

GENDER_OPTIONS: list[Gender] = ["male", "female"]

# Ordered low to high, matching the model's own vocabulary verbatim.
PITCH_OPTIONS: list[Pitch] = [
    "very low pitch",
    "low pitch",
    "moderate pitch",
    "high pitch",
    "very high pitch",
]

AGE_OPTIONS: list[AgeGroup] = ["child", "teenager", "young adult", "middle-aged", "elderly"]

DEFAULT_PITCH: Pitch = "moderate pitch"
