"""Resolve a SpeechRequest's voice_id/gender to a concrete Voice (FR-005)."""

from __future__ import annotations

from backend.app.data.voices import DEFAULT_VOICE_BY_GENDER
from backend.app.models.voice import Voice


class VoiceResolutionError(Exception):
    def __init__(self, message: str, valid_alternatives: list[str]) -> None:
        self.valid_alternatives = valid_alternatives
        super().__init__(message)


def resolve_voice(
    voices: list[Voice], *, voice_id: str | None = None, gender: str | None = None
) -> Voice:
    """Priority: explicit voice_id > gender's default > overall default."""
    if voice_id is not None:
        for v in voices:
            if v.id == voice_id:
                return v
        raise VoiceResolutionError(
            f"voice '{voice_id}' not found", [v.id for v in voices]
        )

    if gender is not None:
        default_id = DEFAULT_VOICE_BY_GENDER.get(gender)
        candidates = [v for v in voices if v.gender == gender]
        if not candidates:
            raise VoiceResolutionError(
                f"no voice available for gender '{gender}'",
                sorted({v.gender for v in voices}),
            )
        for v in candidates:
            if v.id == default_id:
                return v
        return candidates[0]

    return voices[0]
