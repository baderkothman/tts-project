"""Arabic voice catalogue.

The 16 Microsoft Arabic locales, verified by enumerating the live voice list and
cross-checked against Microsoft's published Arabic voice table (research R2).

Dialect families are claimed only where a provider publishes a distinct locale
(FR-027). ar-LY and ar-YE are catalogued *without* a family: asserting one would
exceed what the vendor documents, which Constitution V forbids.
"""

from __future__ import annotations

from backend.app.models.voice import Dialect, VoiceConfig

# locale -> (dialect family or None, female voice, male voice)
_ARABIC_LOCALES: dict[str, tuple[Dialect | None, str, str]] = {
    "ar-SA": (Dialect.MSA, "ZariyahNeural", "HamedNeural"),
    "ar-EG": (Dialect.EGYPTIAN, "SalmaNeural", "ShakirNeural"),
    "ar-AE": (Dialect.GULF, "FatimaNeural", "HamdanNeural"),
    "ar-KW": (Dialect.GULF, "NouraNeural", "FahedNeural"),
    "ar-QA": (Dialect.GULF, "AmalNeural", "MoazNeural"),
    "ar-BH": (Dialect.GULF, "LailaNeural", "AliNeural"),
    "ar-OM": (Dialect.GULF, "AyshaNeural", "AbdullahNeural"),
    "ar-IQ": (Dialect.GULF, "RanaNeural", "BasselNeural"),
    "ar-LB": (Dialect.LEVANTINE, "LaylaNeural", "RamiNeural"),
    "ar-SY": (Dialect.LEVANTINE, "AmanyNeural", "LaithNeural"),
    "ar-JO": (Dialect.LEVANTINE, "SanaNeural", "TaimNeural"),
    "ar-MA": (Dialect.MAGHREBI, "MounaNeural", "JamalNeural"),
    "ar-DZ": (Dialect.MAGHREBI, "AminaNeural", "IsmaelNeural"),
    "ar-TN": (Dialect.MAGHREBI, "ReemNeural", "HediNeural"),
    "ar-LY": (None, "ImanNeural", "OmarNeural"),
    "ar-YE": (None, "MaryamNeural", "SalehNeural"),
}

LOCALE_DISPLAY: dict[str, str] = {
    "ar-SA": "Saudi Arabia", "ar-EG": "Egypt", "ar-AE": "UAE",
    "ar-KW": "Kuwait", "ar-QA": "Qatar", "ar-BH": "Bahrain",
    "ar-OM": "Oman", "ar-IQ": "Iraq", "ar-LB": "Lebanon",
    "ar-SY": "Syria", "ar-JO": "Jordan", "ar-MA": "Morocco",
    "ar-DZ": "Algeria", "ar-TN": "Tunisia", "ar-LY": "Libya",
    "ar-YE": "Yemen",
}

DEFAULT_LOCALE = "ar-SA"


def _build(provider: str, supports_ssml: bool) -> list[VoiceConfig]:
    """Build the catalogue for a Microsoft-voice-family provider.

    Edge and Azure serve the *same* underlying neural voices; they differ in
    the control surface (Azure exposes SSML, Edge does not), not the roster.
    """
    voices: list[VoiceConfig] = []
    default_fallback = f"{provider}:{DEFAULT_LOCALE}-female"

    for locale, (dialect, female, male) in _ARABIC_LOCALES.items():
        for gender, short in (("female", female), ("male", male)):
            vid = f"{provider}:{locale}-{gender}"
            voices.append(
                VoiceConfig(
                    id=vid,
                    provider=provider,
                    provider_voice_id=f"{locale}-{short}",
                    locale=locale,
                    dialect=dialect,
                    gender=gender,
                    supports_streaming=True,
                    # No Microsoft Arabic voice exposes speaking styles or
                    # roles (research R2). Emotion is prosody-approximated.
                    supports_emotions=False,
                    supports_ssml=supports_ssml,
                    latency_class="standard",
                    fallback_voice_id=None if vid == default_fallback else default_fallback,
                    display_name=f"{LOCALE_DISPLAY[locale]} — {short.replace('Neural', '')} ({gender})",
                )
            )
    return voices


EDGE_VOICES: list[VoiceConfig] = _build("edge", supports_ssml=False)
AZURE_VOICES: list[VoiceConfig] = _build("azure", supports_ssml=True)

# ElevenLabs publishes no Arabic locale codes; its Arabic voices vary by accent
# without a documented locale. They are catalogued with dialect=None rather
# than an inferred family (FR-027, research R2).
ELEVENLABS_VOICES: list[VoiceConfig] = [
    VoiceConfig(
        id="elevenlabs:rachel",
        provider="elevenlabs",
        provider_voice_id="21m00Tcm4TlvDq8ikWAM",
        locale="ar-SA",
        dialect=None,
        gender="female",
        supports_streaming=True,
        supports_emotions=True,
        supports_ssml=False,
        latency_class="low",
        fallback_voice_id="edge:ar-SA-female",
        display_name="Rachel (multilingual, Arabic-capable)",
    ),
    VoiceConfig(
        id="elevenlabs:adam",
        provider="elevenlabs",
        provider_voice_id="pNInz6obpgDQGcFmaJgB",
        locale="ar-SA",
        dialect=None,
        gender="male",
        supports_streaming=True,
        supports_emotions=True,
        supports_ssml=False,
        latency_class="low",
        fallback_voice_id="edge:ar-SA-male",
        display_name="Adam (multilingual, Arabic-capable)",
    ),
]

ALL_LOCALES: list[str] = list(_ARABIC_LOCALES.keys())


def locales_for_dialect(dialect: Dialect) -> list[str]:
    return [loc for loc, (d, _, _) in _ARABIC_LOCALES.items() if d == dialect]


def dialect_for_locale(locale: str) -> Dialect | None:
    entry = _ARABIC_LOCALES.get(locale)
    return entry[0] if entry else None
