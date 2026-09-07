"""Provider-specific markup construction (FR-041, research R4).

SSML is built programmatically with every interpolated value escaped, so
markup-like user text can never alter the synthesis instructions sent to a
provider — injection is prevented by construction, not by filtering
(Constitution VII, FR-041).

No phoneme mechanism is portable across providers (research R4): ElevenLabs
restricts phonemes to English, Groq's Orpheus Arabic model accepts no markup
at all, and the Edge client escapes its own input and accepts none. So
phoneme markup is emitted ONLY when the target provider's Capabilities
declare `phoneme=True` (none in this project's catalogue currently do);
everywhere else, correction stays in the orthographic rewriting already
applied by `pronunciation.py`.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from backend.app.models.voice import Capabilities, EmotionStyle, VoiceConfig

# Style -> (rate %, pitch %, volume %) prosody approximation, as plain numbers.
# No Arabic voice in this catalogue exposes native styles (research R2/R3), so
# every style is expressed as a prosody shift, never as an emotion attribute.
# Kept as numbers (not provider-formatted strings) because providers disagree
# on units: edge-tts requires pitch in whole Hz while rate/volume are percent
# (verified against edge_tts.data_classes.TTSConfig's own validation regexes).
# Each adapter formats these itself; `build_ssml` below is currently unused
# by any adapter in the catalogue (no provider both accepts SSML and lacks a
# credential gate) but is kept as the capability-gated SSML path for a future
# SSML-capable adapter (Constitution II — providers vary, the interface does not).
_STYLE_PROSODY: dict[EmotionStyle, tuple[float, float, float]] = {
    EmotionStyle.NEUTRAL: (0, 0, 0),
    EmotionStyle.HAPPY: (8, 6, 0),
    EmotionStyle.EXCITED: (18, 12, 5),
    EmotionStyle.SAD: (-12, -8, -5),
    EmotionStyle.WARM: (-5, 2, 0),
    EmotionStyle.CALM: (-10, -2, -5),
    EmotionStyle.SERIOUS: (-5, -4, 0),
    EmotionStyle.CONVERSATIONAL: (2, 0, 0),
}


def prosody_for_style(style: EmotionStyle) -> tuple[float, float, float]:
    """(rate_pct, pitch_pct, volume_pct) numbers for a style approximation.

    Callers format these into their own provider's required units.
    """
    return _STYLE_PROSODY.get(style, _STYLE_PROSODY[EmotionStyle.NEUTRAL])


def build_ssml(
    text: str,
    voice: VoiceConfig,
    *,
    rate: str = "+0%",
    pitch: str = "+0%",
    volume: str = "+0%",
) -> str:
    """Build SSML with the text escaped, so it can never be interpreted as
    markup regardless of what a user submitted."""
    safe_text = escape(text)
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{escape(voice.locale)}">'
        f'<voice name="{escape(voice.provider_voice_id)}">'
        f'<prosody rate="{escape(rate)}" pitch="{escape(pitch)}" volume="{escape(volume)}">'
        f"{safe_text}"
        "</prosody></voice></speak>"
    )


def maybe_add_phoneme(text: str, ipa: str, capabilities: Capabilities) -> str:
    """Wrap `text` in a <phoneme> tag only if the provider supports it.

    `ipa` and `text` are both escaped; the tag structure itself cannot be
    influenced by their content.
    """
    if not capabilities.phoneme:
        return escape(text)
    return f'<phoneme alphabet="ipa" ph="{escape(ipa)}">{escape(text)}</phoneme>'
