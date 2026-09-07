"""Arabic normalization for speech synthesis.

CRITICAL (Constitution III): this module deliberately does NOT perform the
hamza / taa-marbuta / alif-maqsura folding common in Arabic NLP. That folding is
a *search-and-retrieval* technique. It is correct for matching and wrong for
speech, because it changes how a word is pronounced and can change its meaning:

    أَسِف  (sorry)        vs  آسف   — different hamza, different word
    مدرسة (school)       vs  مدرسه  (his teacher) — taa marbuta carries meaning
    على   (on)           vs  علي   (Ali, a name) — alif maqsura vs yaa

Folding these would silently degrade every synthesis. Only transformations that
preserve meaning are applied here.
"""

from __future__ import annotations

import re
import unicodedata

# Tatweel/kashida: pure typographic elongation, carries no phonetic value.
TATWEEL = "ـ"

# Arabic diacritics (tashkeel). PRESERVED, never stripped (FR-008) — they are
# the author's explicit pronunciation instruction.
TASHKEEL = "ً-ْٰٓ-ٕ"

# Zero-width and bidi control characters. These are invisible, can corrupt
# provider payloads, and never affect pronunciation.
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")

# C0/C1 controls except tab/newline/carriage return.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Arabic-Indic digits -> ASCII, so one number path handles both (FR-009).
_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Punctuation normalization: Arabic forms are kept where they cue prosody
# correctly, and stray Latin forms mapped onto them.
_PUNCT_MAP = {
    "?": "؟",
    ";": "؛",
    "٪": "%",   # Arabic percent sign -> ASCII for the numbers stage
    "٫": ".",   # Arabic decimal separator
    "٬": ",",   # Arabic thousands separator
}

_MULTISPACE = re.compile(r"[ \t ]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([،؛؟!.,:])")


def normalize(text: str) -> str:
    """Normalize Arabic text without changing meaning."""
    if not text:
        return text

    # NFC keeps composed forms and folds compatibility presentation forms
    # (e.g. Arabic ligature blocks) into their canonical equivalents.
    text = unicodedata.normalize("NFC", text)

    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub("", text)
    text = text.replace(TATWEEL, "")
    text = text.translate(_ARABIC_INDIC)

    for src, dst in _PUNCT_MAP.items():
        text = text.replace(src, dst)

    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _MULTISPACE.sub(" ", text)

    return text.strip()


def strip_tashkeel(text: str) -> str:
    """Remove diacritics.

    NOT part of the pipeline. Exposed only for comparison and testing — the
    pipeline preserves diacritics (FR-008).
    """
    return re.sub(f"[{TASHKEEL}]", "", text)


def has_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)
