"""Dialect / locale / voice resolution (FR-025, FR-025a, FR-026).

Resolves a request's locale, dialect family, or explicit voice id to a concrete
`VoiceConfig` served by a concrete provider — rejecting mismatches with the
valid alternatives named, never falling back silently to an unrelated voice.
"""

from __future__ import annotations

from backend.app.data.voices import DEFAULT_LOCALE
from backend.app.models.voice import Dialect, VoiceConfig
from backend.app.providers.base import TTSProvider


class VoiceResolutionError(Exception):
    def __init__(self, message: str, valid_alternatives: list[str]) -> None:
        self.valid_alternatives = valid_alternatives
        super().__init__(message)


def resolve_voice(
    provider: TTSProvider,
    voices: list[VoiceConfig],
    *,
    voice_id: str | None = None,
    locale: str | None = None,
    dialect: Dialect | None = None,
) -> VoiceConfig:
    """Resolve a voice from the given provider's own voice list.

    Priority: explicit voice_id > explicit locale > dialect family > default.
    """
    if voice_id is not None:
        for v in voices:
            if v.id == voice_id:
                if v.provider != provider.id:
                    raise VoiceResolutionError(
                        f"voice '{voice_id}' does not belong to provider '{provider.id}'",
                        [x.id for x in voices],
                    )
                return v
        raise VoiceResolutionError(
            f"voice '{voice_id}' not found on provider '{provider.id}'",
            [v.id for v in voices],
        )

    if locale is not None:
        candidates = [v for v in voices if v.locale == locale]
        if not candidates:
            raise VoiceResolutionError(
                f"locale '{locale}' not supported by provider '{provider.id}'",
                sorted({v.locale for v in voices}),
            )
        return candidates[0]

    if dialect is not None:
        # Match each voice's OWN declared dialect, not a locale-string lookup
        # (dropped after a real bug: Groq's Saudi-dialect voices and Edge's
        # MSA-trained ar-SA voice share the locale string "ar-SA" but carry
        # different `dialect` values — locale and dialect authenticity are
        # independent axes here, see docs/DIALECT_EVALUATION.md — so routing
        # must key on `dialect` directly, which every voice already carries).
        candidates = [v for v in voices if v.dialect == dialect]
        if not candidates:
            raise VoiceResolutionError(
                f"dialect family '{dialect.value}' not servable by provider '{provider.id}'",
                sorted({v.dialect.value for v in voices if v.dialect}),
            )
        return candidates[0]

    default = [v for v in voices if v.locale == DEFAULT_LOCALE]
    return default[0] if default else voices[0]
