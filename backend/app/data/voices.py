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
    """Build the catalogue for a Microsoft-neural-voice-family provider."""
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

# Groq's Orpheus Arabic model: a genuinely dialect-trained (Saudi/Gulf) voice
# family, distinct from the MSA-trained Microsoft voices above even though it
# shares the ar-SA locale (research R1). Six voices, confirmed against the
# vendor's Orpheus Arabic model page (fetched 2026-09-07): 3 male, 3 female.
# provider_voice_id is lowercase deliberately: the live API rejects the
# capitalized form documented on the vendor's page ("voice must be one of
# [fahad sultan noura lulwa aisha abdullah]") — caught by a real 400 response
# once a GROQ_API_KEY was configured, not assumed from the docs (Constitution V).
GROQ_VOICES: list[VoiceConfig] = [
    VoiceConfig(
        id=f"groq:ar-SA-{name.lower()}",
        provider="groq",
        provider_voice_id=name.lower(),
        locale="ar-SA",
        dialect=Dialect.GULF,
        gender=gender,
        supports_streaming=False,
        supports_emotions=False,
        supports_ssml=False,
        latency_class="standard",
        fallback_voice_id=None if name == "Abdullah" else "groq:ar-SA-abdullah",
        display_name=f"{name} — Saudi dialect ({gender})",
    )
    for name, gender in (
        ("Abdullah", "male"), ("Fahad", "male"), ("Sultan", "male"),
        ("Lulwa", "female"), ("Noura", "female"), ("Aisha", "female"),
    )
]

# ElevenLabs publishes no Arabic locale codes; its Arabic voices vary by accent
# without a documented locale. They are catalogued with dialect=None rather
# than an inferred family (FR-027, research R2).
#
# Voice selection constraint discovered live (docs/TTS_EVALUATION.md): the
# free tier's API rejects calls to public "Voice Library" voices (402
# payment_required) — only voices already present in the account's OWN
# library (`GET /v1/voices`) are callable. "Rachel" (21m00Tcm4TlvDq8ikWAM),
# ElevenLabs' commonly-documented example voice, is a library voice and is
# NOT in this project's configured account by default, so it was replaced
# with "Sarah", one of the ~20 premade voices ElevenLabs gives every new
# account by default — confirmed live: both Sarah and Adam returned real
# Arabic audio (200, non-empty MP3 bytes) with the configured key.
ELEVENLABS_VOICES: list[VoiceConfig] = [
    VoiceConfig(
        id="elevenlabs:sarah",
        provider="elevenlabs",
        provider_voice_id="EXAVITQu4vr4xnSDxMaL",
        locale="ar-SA",
        dialect=None,
        gender="female",
        supports_streaming=True,
        supports_emotions=True,
        supports_ssml=False,
        latency_class="low",
        fallback_voice_id="edge:ar-SA-female",
        display_name="Sarah (multilingual, Arabic-capable)",
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
