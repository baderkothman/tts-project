"""Combines dictionary lookup with diacritizer/G2P output, dialect-scoped (FR-052).

Dictionary lookup (data/pronunciation_dictionary.py) always runs — it is
pure, offline, and instant. The Hugging Face diacritizer/G2P calls only run
as a supplement, and their absence (no HF_TOKEN, no enabled model) degrades
to "dictionary-only correction," never a failure (FR-057).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.data.pronunciation_dictionary import lookup
from backend.app.text_processing.huggingface.diacritizer import diacritize
from backend.app.text_processing.huggingface.g2p import phonemize


@dataclass
class TokenCorrection:
    token: str
    normalized: str | None = None
    diacritized: str | None = None
    phonemes: str | None = None
    changes: list[str] = field(default_factory=list)


async def correct_token(
    token: str, *, dialect: str | None, hf_token: str | None
) -> TokenCorrection:
    entry = lookup(token, dialect=dialect)
    correction = TokenCorrection(token=token)

    if entry is not None:
        correction.normalized = entry.normalized
        correction.diacritized = entry.diacritized
        correction.phonemes = entry.phonemes
        if entry.normalized and entry.normalized != token:
            correction.changes.append(f"pronunciation dictionary: {token} -> {entry.normalized}")
        if entry.diacritized:
            correction.changes.append("diacritic added (dictionary)")
        return correction

    # No dictionary entry — try the Hugging Face diacritizer/G2P as a
    # supplement. Both degrade silently to "no change" when unavailable,
    # per FR-057; the caller sees an empty `changes` list, not an error.
    diac = await diacritize(token, hf_token=hf_token)
    if diac.diacritized and diac.diacritized != token:
        correction.diacritized = diac.diacritized
        correction.changes.append("diacritic added (Hugging Face)")

    g2p = await phonemize(token, hf_token=hf_token)
    if g2p.phonemes:
        correction.phonemes = g2p.phonemes

    return correction
