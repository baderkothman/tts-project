"""Arabic date verbalization (FR-010).

Handles numeric (27/09/2026, 2026-09-27) and mixed (27 سبتمبر 2026) formats,
producing a spoken-form Arabic date rather than separated numbers.
"""

from __future__ import annotations

import re

from backend.app.text_processing.numbers import integer_to_arabic

MONTHS_MSA = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# Recognize the MSA month names (and a couple of common Gulf/Levant variants)
# so a mixed-format date like "27 سبتمبر 2026" is matched, not just numeric ones.
_MONTH_ALIASES: dict[str, int] = {name: i for i, name in enumerate(MONTHS_MSA) if name}
_MONTH_ALIASES.update({
    "كانون الثاني": 1, "شباط": 2, "آذار": 3, "نيسان": 4, "أيار": 5, "حزيران": 6,
    "تموز": 7, "آب": 8, "أيلول": 9, "تشرين الأول": 10, "تشرين الثاني": 11, "كانون الأول": 12,
})

# `\b` is deliberately NOT used here: Python's default Unicode-aware regex
# treats Arabic letters as `\w`, so `\b` finds no boundary between a
# no-space proclitic like "و" (and) and a following digit — a very common
# Arabic writing pattern ("و27/09/2026"). This was caught by testing a
# realistic mixed sentence during implementation, not assumed (Constitution
# V). Digit-adjacency lookaround (matching numbers.py's approach) is
# unaffected by the Arabic-letter-is-\w behavior.
_DMY_SLASH = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_MIXED = re.compile(
    r"(?<!\d)(\d{1,2})\s+(" + "|".join(re.escape(m) for m in _MONTH_ALIASES) + r")\s+(\d{4})(?!\d)"
)


def _spoken_date(day: int, month: int, year: int) -> str:
    day_words = integer_to_arabic(day)
    month_name = MONTHS_MSA[month] if 1 <= month <= 12 else str(month)
    year_words = integer_to_arabic(year)
    return f"{day_words} {month_name} {year_words}"


def verbalize_dates(text: str) -> str:
    """Replace recognized date spans with spoken Arabic dates.

    Mixed-format dates (which already carry the month name) are handled first
    so the numeric-date patterns don't also try to consume their day/year.
    """

    def _mixed(m: re.Match[str]) -> str:
        day, month_name, year = int(m.group(1)), m.group(2), int(m.group(3))
        return _spoken_date(day, _MONTH_ALIASES[month_name], year)

    def _dmy(m: re.Match[str]) -> str:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _spoken_date(day, month, year)

    def _iso(m: re.Match[str]) -> str:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _spoken_date(day, month, year)

    text = _MIXED.sub(_mixed, text)
    text = _ISO.sub(_iso, text)
    text = _DMY_SLASH.sub(_dmy, text)
    return text
