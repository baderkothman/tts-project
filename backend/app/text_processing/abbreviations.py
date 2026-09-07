"""Arabic and Latin abbreviation handling (FR-012).

Two distinct behaviors, because the two failure modes are different:
  - Arabic abbreviations (د. م.) are EXPANDED to the word they stand for —
    an Arabic TTS engine has no notion of "read this dot as an abbreviation".
  - Latin initialisms are split into either letter-by-letter spelling
    (API, AWS, AI, CEO) or, for a few, a fully spelled acronym read as one
    word — set case by case since English orthography doesn't mark this.
"""

from __future__ import annotations

import re

# Arabic abbreviation -> full word it stands for.
_ARABIC_EXPANSIONS: dict[str, str] = {
    "د.": "دكتور",
    "أ.د.": "أستاذ دكتور",
    "م.": "مهندس",
    "أ.": "أستاذ",
    "ص.ب.": "صندوق بريد",
    "ط.": "طبعة",
    "ج.": "جزء",
}

# English letter -> Arabic spoken letter name (for spelled-out initialisms).
_LATIN_LETTER_NAMES: dict[str, str] = {
    "A": "إيه", "B": "بي", "C": "سي", "D": "دي", "E": "إي", "F": "إف",
    "G": "جي", "H": "إتش", "I": "آي", "J": "جيه", "K": "كيه", "L": "إل",
    "M": "إم", "N": "إن", "O": "أوه", "P": "بي", "Q": "كيو", "R": "آر",
    "S": "إس", "T": "تي", "U": "يو", "V": "في", "W": "دبليو", "X": "إكس",
    "Y": "واي", "Z": "زد",
}

# Acronyms conventionally read as one word, not spelled letter by letter.
_READ_AS_WORD: dict[str, str] = {
    "AI": "إيه آي",  # commonly spoken as letters in Arabic tech contexts
    "NASA": "ناسا",
    "UNESCO": "يونسكو",
}

_ARABIC_ABBR_PATTERN = re.compile(
    "|".join(re.escape(k) for k in sorted(_ARABIC_EXPANSIONS, key=len, reverse=True))
)
# `\b` deliberately not used: Arabic letters are `\w` under Python's default
# Unicode regex, so a no-space proclitic ("وAPI") would find no boundary
# between the Arabic letter and the Latin run (same class of bug as
# dates.py's date patterns — caught the same way, by testing realistic
# no-space Arabic text during implementation).
_LATIN_INITIALISM = re.compile(r"(?<![A-Za-z])([A-Z]{2,6})(?![A-Za-z])")


def _spell_out(letters: str) -> str:
    return " ".join(_LATIN_LETTER_NAMES.get(c, c) for c in letters)


def verbalize_abbreviations(text: str) -> str:
    text = _ARABIC_ABBR_PATTERN.sub(lambda m: _ARABIC_EXPANSIONS[m.group(0)], text)

    def _latin(m: re.Match[str]) -> str:
        token = m.group(1)
        if token in _READ_AS_WORD:
            return _READ_AS_WORD[token]
        return _spell_out(token)

    text = _LATIN_INITIALISM.sub(_latin, text)
    return text
