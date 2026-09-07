"""DialectProfile records (FR-049).

Six profiles, per spec.md's minimum: msa, levantine, lebanese, gulf, saudi,
egyptian. `lebanese` and `saudi` are deliberately *narrower* than the
`Dialect` enum's `levantine`/`gulf` families — no integrated TTS provider
publishes a Lebanon- or Saudi-specific locale distinct from those broader
families (research.md R2), so the extra granularity lives here, honestly,
rather than being invented as a new `Dialect` enum value no provider backs.

`normalization_rules` stays empty for every profile at this stage: no rule in
`text_processing/dictionary.py` targets dialect vocabulary specifically yet,
so there is nothing to reference — and inventing a placeholder reference
would violate FR-050's "never fake" requirement.
"""

from __future__ import annotations

from backend.app.models.dialect import DialectProfile
from backend.app.models.voice import Dialect

DIALECT_PROFILES: list[DialectProfile] = [
    DialectProfile(
        id="msa",
        name="Modern Standard Arabic",
        region=None,
        dialect_family=Dialect.MSA,
        locale="ar-SA",
        aliases=["fusha", "standard"],
        preferred_tts_models=[],
        fallback_tts_models=["edge:ar-SA-female", "edge:ar-SA-male"],
    ),
    DialectProfile(
        id="levantine",
        name="Levantine Arabic",
        region="Levant (Lebanon, Syria, Jordan, Palestine)",
        dialect_family=Dialect.LEVANTINE,
        locale=None,  # spans multiple locales; no single one represents it
        aliases=["shami"],
        preferred_tts_models=[],
        fallback_tts_models=[
            "edge:ar-LB-female", "edge:ar-LB-male",
            "edge:ar-SY-female", "edge:ar-SY-male",
            "edge:ar-JO-female", "edge:ar-JO-male",
        ],
    ),
    DialectProfile(
        id="lebanese",
        name="Lebanese Arabic",
        region="Lebanon",
        dialect_family=Dialect.LEVANTINE,  # no provider publishes a narrower locale
        locale="ar-LB",
        aliases=["lubnani"],
        preferred_tts_models=[],  # no HF candidate cleared R11 for this dialect yet
        fallback_tts_models=["edge:ar-LB-female", "edge:ar-LB-male"],
    ),
    DialectProfile(
        id="gulf",
        name="Gulf Arabic",
        region="Arabian Gulf (UAE, Kuwait, Qatar, Bahrain, Oman, Iraq)",
        dialect_family=Dialect.GULF,
        locale=None,
        aliases=["khaleeji"],
        preferred_tts_models=[],
        fallback_tts_models=[
            "edge:ar-AE-female", "edge:ar-AE-male",
            "groq:ar-SA-abdullah", "groq:ar-SA-lulwa",
        ],
    ),
    DialectProfile(
        id="saudi",
        name="Saudi Arabic",
        region="Saudi Arabia",
        dialect_family=Dialect.GULF,  # narrower than the Gulf family Edge/Groq route on
        locale="ar-SA",
        aliases=["saudi arabic", "khaleeji-saudi"],
        # Groq's Orpheus model is genuinely dialect-trained for Saudi/Gulf
        # speech (research R1), unlike Edge's ar-SA MSA voice — this is the
        # one profile where an *existing* provider is itself the best-scoring
        # architecture found so far, not merely a fallback.
        preferred_tts_models=[],
        fallback_tts_models=["groq:ar-SA-abdullah", "groq:ar-SA-lulwa"],
    ),
    DialectProfile(
        id="egyptian",
        name="Egyptian Arabic",
        region="Egypt",
        dialect_family=Dialect.EGYPTIAN,
        locale="ar-EG",
        aliases=["masri"],
        # "egyptian-tts-chatterbox" is eligible per data/hf_model_registry.py
        # but NOT listed here yet — it is wired in only after
        # scripts/observe_dialect_tts.py confirms live that it actually
        # produces recognizable Egyptian speech (FR-061, Constitution V;
        # tasks.md T144-T145 sequence). Until then this profile's
        # architecture recommendation is honestly "existing TTS only".
        preferred_tts_models=[],
        fallback_tts_models=["edge:ar-EG-female", "edge:ar-EG-male"],
    ),
]


def get(profile_id: str) -> DialectProfile | None:
    for p in DIALECT_PROFILES:
        if p.id == profile_id:
            return p
    return None
