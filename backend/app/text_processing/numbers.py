"""Arabic number verbalization (FR-009, FR-014).

Converts digits to spoken Arabic words. Raw TTS engines read "1,250" as
disconnected digits or mis-parse the separator; this stage removes that failure
mode entirely by handing the engine words instead of numerals.

Masculine citation forms are used throughout — that is how numbers are read
aloud in isolation in MSA.
"""

from __future__ import annotations

import re

ONES = [
    "صفر", "واحد", "اثنان", "ثلاثة", "أربعة",
    "خمسة", "ستة", "سبعة", "ثمانية", "تسعة",
]
TEENS = [
    "عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر",
    "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر",
]
TENS = [
    "", "عشرة", "عشرون", "ثلاثون", "أربعون",
    "خمسون", "ستون", "سبعون", "ثمانون", "تسعون",
]
HUNDREDS = [
    "", "مئة", "مئتان", "ثلاثمئة", "أربعمئة",
    "خمسمئة", "ستمئة", "سبعمئة", "ثمانمئة", "تسعمئة",
]

# (singular, dual, plural) for each power of a thousand.
SCALES: list[tuple[str, str, str]] = [
    ("", "", ""),
    ("ألف", "ألفان", "آلاف"),
    ("مليون", "مليونان", "ملايين"),
    ("مليار", "ملياران", "مليارات"),
    ("تريليون", "تريليونان", "تريليونات"),
]


def _under_thousand(n: int) -> str:
    """Verbalize 0-999."""
    parts: list[str] = []
    hundreds, rest = divmod(n, 100)

    if hundreds:
        parts.append(HUNDREDS[hundreds])

    if rest:
        if rest < 10:
            parts.append(ONES[rest])
        elif rest < 20:
            parts.append(TEENS[rest - 10])
        else:
            tens, units = divmod(rest, 10)
            # Arabic puts the unit BEFORE the ten, joined by "و":
            # 25 -> خمسة وعشرون  (literally "five and twenty")
            if units:
                parts.append(f"{ONES[units]} و{TENS[tens]}")
            else:
                parts.append(TENS[tens])

    return " و".join(parts) if parts else ONES[0]


def _scale_word(count: int, scale_index: int) -> str:
    """Apply Arabic scale agreement: singular / dual / plural.

    Arabic has a dual form, and 3-10 take the plural while 11+ revert to the
    singular. Getting this wrong is immediately audible to a native speaker.
    """
    singular, dual, plural = SCALES[scale_index]
    if count == 1:
        return singular
    if count == 2:
        return dual
    if 3 <= count <= 10:
        return plural
    return singular


def integer_to_arabic(n: int) -> str:
    """Verbalize an integer of any practical size."""
    if n < 0:
        return f"سالب {integer_to_arabic(abs(n))}"
    if n == 0:
        return ONES[0]

    # Split into groups of three, least significant first.
    groups: list[int] = []
    while n:
        n, rem = divmod(n, 1000)
        groups.append(rem)

    parts: list[str] = []
    for idx in range(len(groups) - 1, -1, -1):
        group = groups[idx]
        if not group:
            continue
        if idx == 0:
            parts.append(_under_thousand(group))
        else:
            scale = _scale_word(group, idx)
            # 1000 is just "ألف", not "واحد ألف"; 2000 is the dual "ألفان".
            if group in (1, 2):
                parts.append(scale)
            else:
                parts.append(f"{_under_thousand(group)} {scale}")

    return " و".join(parts)


def decimal_to_arabic(whole: str, frac: str) -> str:
    """Verbalize a decimal: 25.5 -> خمسة وعشرون فاصلة خمسة."""
    whole_words = integer_to_arabic(int(whole))
    # Read fractional digits individually — "٫٥٠" is not "fifty".
    frac_words = " ".join(ONES[int(d)] for d in frac)
    return f"{whole_words} فاصلة {frac_words}"


def digits_to_sequence(digits: str) -> str:
    """Read digits one by one, for identifiers rather than quantities (FR-014).

    A phone number is not a cardinal quantity; reading +96170123456 as a single
    enormous number is wrong, so identifiers get digit-by-digit treatment.
    """
    return " ".join(ONES[int(d)] for d in digits if d.isdigit())


# --- Pattern-level replacement -------------------------------------------

# An identifier: a long run of digits, or one carrying a leading +/00 country
# code, or grouped like a phone number. Threshold of 7 keeps years (2026) and
# ordinary quantities out.
_IDENTIFIER = re.compile(r"(?<![\d.,])(\+\d{6,}|00\d{6,}|\d{7,})(?![\d.,])")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DECIMAL = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)(?![\d])")
_GROUPED = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?![\d])")
_PLAIN = re.compile(r"(?<![\d.,+])\d+(?![\d.,])")


def verbalize_numbers(text: str) -> str:
    """Replace numeric spans with Arabic words.

    Order matters: identifiers and percentages are consumed before the generic
    integer rule, so a phone number is never read as a quantity and "%" is never
    orphaned from its value.
    """

    def _identifier(m: re.Match[str]) -> str:
        raw = m.group(1)
        prefix = "زائد " if raw.startswith("+") else ""
        return prefix + digits_to_sequence(raw)

    def _percent(m: re.Match[str]) -> str:
        value = m.group(1)
        if "." in value:
            whole, frac = value.split(".")
            words = decimal_to_arabic(whole, frac)
        else:
            words = integer_to_arabic(int(value))
        return f"{words} بالمئة"

    def _decimal(m: re.Match[str]) -> str:
        return decimal_to_arabic(m.group(1).replace(",", ""), m.group(2))

    def _grouped(m: re.Match[str]) -> str:
        return integer_to_arabic(int(m.group(0).replace(",", "")))

    def _plain(m: re.Match[str]) -> str:
        return integer_to_arabic(int(m.group(0)))

    text = _IDENTIFIER.sub(_identifier, text)
    text = _PERCENT.sub(_percent, text)
    text = _DECIMAL.sub(_decimal, text)
    text = _GROUPED.sub(_grouped, text)
    text = _PLAIN.sub(_plain, text)
    return text
