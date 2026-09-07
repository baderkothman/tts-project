"""Arabic currency verbalization (FR-011).

Produces "<amount> <currency name>" in the correct Arabic word order for
symbol-prefixed ($25), code-suffixed (25 USD), and Arabic-name (100 ريال)
forms, including subunits (1,250.50 دولار -> دولارات ...و٥٠ سنتاً).
"""

from __future__ import annotations

import re

from backend.app.text_processing.numbers import integer_to_arabic

# symbol/code -> (singular name, plural name, subunit singular, subunit plural)
_CURRENCIES: dict[str, tuple[str, str, str, str]] = {
    "$": ("دولار", "دولارات", "سنت", "سنتات"),
    "USD": ("دولار", "دولارات", "سنت", "سنتات"),
    "SAR": ("ريال سعودي", "ريالات سعودية", "هللة", "هللات"),
    "دولار": ("دولار", "دولارات", "سنت", "سنتات"),
    "ريال": ("ريال", "ريالات", "هللة", "هللات"),
    "€": ("يورو", "يورو", "سنت", "سنتات"),
    "EUR": ("يورو", "يورو", "سنت", "سنتات"),
    "£": ("جنيه إسترليني", "جنيهات إسترلينية", "بنس", "بنسات"),
    "GBP": ("جنيه إسترليني", "جنيهات إسترلينية", "بنس", "بنسات"),
}


def _currency_name(unit: str, count: int) -> str:
    singular, plural, _, _ = _CURRENCIES[unit]
    if count == 1:
        return singular
    if 3 <= count <= 10:
        return plural
    return singular


def _amount_words(amount_str: str, unit: str) -> str:
    amount_str = amount_str.replace(",", "")
    if "." in amount_str:
        whole_s, frac_s = amount_str.split(".")
        whole, cents = int(whole_s), int(frac_s.ljust(2, "0")[:2])
    else:
        whole, cents = int(amount_str), 0

    _, _, sub_sing, sub_plural = _CURRENCIES[unit]
    whole_words = f"{integer_to_arabic(whole)} {_currency_name(unit, whole)}"

    if not cents:
        return whole_words

    sub_name = sub_sing if cents == 1 else (sub_plural if 3 <= cents <= 10 else sub_sing)
    return f"{whole_words} و{integer_to_arabic(cents)} {sub_name}"


_NUM = r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?"

# $25 / £25 / €25  (symbol before amount)
_SYMBOL_PREFIX = re.compile(rf"([$€£])\s?({_NUM})")
# 25 USD / 100 SAR  (ISO code after amount)
_CODE_SUFFIX = re.compile(rf"({_NUM})\s?(USD|SAR|EUR|GBP)\b")
# 100 ريال / 1,250.50 دولار  (Arabic name after amount)
_ARABIC_SUFFIX = re.compile(rf"({_NUM})\s?(ريال|دولار)\b")


def verbalize_currencies(text: str) -> str:
    def _prefix(m: re.Match[str]) -> str:
        return _amount_words(m.group(2), m.group(1))

    def _suffix(m: re.Match[str]) -> str:
        return _amount_words(m.group(1), m.group(2))

    text = _SYMBOL_PREFIX.sub(_prefix, text)
    text = _CODE_SUFFIX.sub(_suffix, text)
    text = _ARABIC_SUFFIX.sub(_suffix, text)
    return text
