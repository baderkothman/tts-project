"""The Saudi voice catalogue — 6 voices, one provider (FR-002, FR-003).

Groq's Orpheus Arabic model (`canopylabs/orpheus-arabic-saudi`) is genuinely
Saudi/Gulf-dialect-trained (research.md R1) and publishes six voices, evenly
split by gender — real, live-verified in the prior feature
(`001-arabic-tts-prototype`), not invented to satisfy this feature's "at
least one male, one female" requirement.
"""

from __future__ import annotations

from backend.app.models.voice import Voice

_MODEL = "canopylabs/orpheus-arabic-saudi"

GROQ_VOICES: list[Voice] = [
    Voice(id="groq:abdullah", name="Abdullah", provider="groq", gender="male", model=_MODEL),
    Voice(id="groq:fahad", name="Fahad", provider="groq", gender="male", model=_MODEL),
    Voice(id="groq:sultan", name="Sultan", provider="groq", gender="male", model=_MODEL),
    Voice(id="groq:lulwa", name="Lulwa", provider="groq", gender="female", model=_MODEL),
    Voice(id="groq:noura", name="Noura", provider="groq", gender="female", model=_MODEL),
    Voice(id="groq:aisha", name="Aisha", provider="groq", gender="female", model=_MODEL),
]

DEFAULT_VOICE_BY_GENDER: dict[str, str] = {
    "male": "groq:abdullah",
    "female": "groq:lulwa",
}
