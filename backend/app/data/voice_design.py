"""Voice-design attribute options this app exposes.

These are not invented — they are drawn from the exact, closed enum the
installed `omnivoice` package validates an `instruct` string against
(`omnivoice.utils.voice_design._INSTRUCT_CATEGORIES`, confirmed by reading
the installed package source: passing anything outside this set raises
`ValueError` from `OmniVoice.generate()`). Only the English-language
categories are relevant here — the package's Chinese-dialect category
(Mandarin topolects) and English-accent category are foreign to an Arabic
TTS product and are intentionally not exposed.

Dialect is deliberately NOT an instruct attribute — see
`backend/app/data/dialects.py` for why it is a `language` parameter
instead.

There is deliberately no `age` attribute here, even though the package's
own instruct vocabulary has one ("child"/"teenager"/"young adult"/
"middle-aged"/"elderly", all accepted without error by `OmniVoice.generate`).
A controlled test run directly against this exact fine-tuned checkpoint
(fixed text/gender/pitch, 5 real generations per category, F0 measured via
`librosa.pyin`, one-way ANOVA + pairwise Welch t-tests) found the 3 middle
categories statistically indistinguishable from each other (pairwise
p=0.36-0.56); even the two extremes that did differ (child vs. elderly,
p=0.003) don't make a useful 2-way control on their own. Rather than expose
a knob that mostly does nothing, no age instruct is ever sent — every
`voice_design` request gets the checkpoint's own untagged default, without
this app claiming that default *is* any particular age.
"""

from __future__ import annotations

from typing import Literal

Gender = Literal["male", "female"]
Pitch = Literal["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"]

GENDER_OPTIONS: list[Gender] = ["male", "female"]

# Ordered low to high, matching the model's own vocabulary verbatim.
PITCH_OPTIONS: list[Pitch] = [
    "very low pitch",
    "low pitch",
    "moderate pitch",
    "high pitch",
    "very high pitch",
]

DEFAULT_PITCH: Pitch = "moderate pitch"
