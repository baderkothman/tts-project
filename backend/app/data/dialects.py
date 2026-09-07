"""The Arabic dialect catalogue this app actually exposes.

Source of truth, in order of precedence:

1. `oddadmix/lahgtna-omnivoice-v2`'s own model card roadmap
   (https://huggingface.co/oddadmix/lahgtna-omnivoice-v2) — the fine-tune's
   *own* claim of which dialects are "completed" versus merely "planned".
   Only the 13 dialects marked completed are listed here; the roadmap's six
   planned dialects (UAE, Kuwait, Qatar, Oman, Jordan, Mauritania) are
   deliberately NOT exposed — a roadmap entry is not a shipped capability.
2. The underlying `omnivoice` package's language resolver
   (`omnivoice.utils.lang_map.LANG_NAME_TO_ID`, inspected directly from the
   installed package source, not guessed), which is what
   `OmniVoice.generate(..., language=...)` actually accepts. This maps each
   dialect name to the ISO 639-3-ish code OmniVoice's base multilingual
   training used.

Two real gaps, disclosed rather than papered over:

- The model has no fixed code specifically for "Palestinian", "Lebanese", or
  "Syrian" — the underlying language map only has one shared code for
  Levantine Arabic (`apc`). All three dialect selections resolve to that
  same `apc` language conditioning; the distinction between them is carried
  by the dialectal vocabulary/spelling the user actually types, not by a
  separate model parameter (see the Lahgtna-specific caveat on
  `Dialect.written_only`, below).
- "Yemeni" is on Lahgtna's own "completed" list, but the installed
  `omnivoice` package's language map has no Yemeni Arabic entry at all
  (verified by reading `omnivoice/utils/lang_map.py` directly — every other
  entry in this table exists there character-for-character). Passing an
  unrecognized language string to the real model silently falls back to
  language-agnostic mode with a logged warning (`_resolve_language` in
  `omnivoice/models/omnivoice.py`) rather than raising, so we do not pass a
  fabricated code for it. It stays in the list because Lahgtna's own card
  claims it, but `language_code` is `None` and `written_only` is `True`:
  the UI must say plainly that dialect conditioning for it comes from the
  Arabic text itself, not from a distinct backend parameter.
"""

from __future__ import annotations

from pydantic import BaseModel


class Dialect(BaseModel):
    id: str
    name_en: str
    name_ar: str
    # The exact string passed to OmniVoice.generate(language=...). None means
    # no distinct code exists for this dialect in the installed omnivoice
    # package's language map — see module docstring.
    language_code: str | None
    # True when this dialect has no distinct `language_code` of its own and
    # therefore relies on the dialectal Arabic the user writes rather than a
    # model parameter to come through in the output.
    written_only: bool = False


# Ordered as on the model card. `language_code` values were read directly
# from the installed `omnivoice` package's `LANG_NAME_TO_ID` map, not
# invented — see module docstring for the two disclosed exceptions.
DIALECTS: list[Dialect] = [
    Dialect(id="egyptian", name_en="Egyptian", name_ar="مصرية", language_code="arz"),
    Dialect(id="saudi", name_en="Saudi (Najdi)", name_ar="سعودية (نجدية)", language_code="ars"),
    Dialect(id="moroccan", name_en="Moroccan", name_ar="مغربية", language_code="ary"),
    Dialect(id="iraqi", name_en="Iraqi", name_ar="عراقية", language_code="acm"),
    Dialect(id="sudanese", name_en="Sudanese", name_ar="سودانية", language_code="apd"),
    Dialect(
        id="palestinian",
        name_en="Palestinian",
        name_ar="فلسطينية",
        language_code="apc",
        written_only=True,
    ),
    Dialect(
        id="lebanese",
        name_en="Lebanese",
        name_ar="لبنانية",
        language_code="apc",
        written_only=True,
    ),
    Dialect(
        id="syrian",
        name_en="Syrian",
        name_ar="سورية",
        language_code="apc",
        written_only=True,
    ),
    Dialect(id="libyan", name_en="Libyan", name_ar="ليبية", language_code="ayl"),
    Dialect(id="tunisian", name_en="Tunisian", name_ar="تونسية", language_code="aeb"),
    Dialect(id="bahraini", name_en="Bahraini", name_ar="بحرينية", language_code="abv"),
    Dialect(id="yemeni", name_en="Yemeni", name_ar="يمنية", language_code=None, written_only=True),
    Dialect(id="algerian", name_en="Algerian", name_ar="جزائرية", language_code="arq"),
    Dialect(
        id="msa",
        name_en="Modern Standard Arabic",
        name_ar="الفصحى",
        language_code="arb",
    ),
]

DIALECT_BY_ID: dict[str, Dialect] = {d.id: d for d in DIALECTS}

DEFAULT_DIALECT_ID = "msa"

# Documented on the model card as "planned", not shipped — never exposed via
# the API. Listed here only so the reason a dialect is absent is traceable
# in one place instead of silently missing.
PLANNED_NOT_IMPLEMENTED = [
    "United Arab Emirates",
    "Kuwait",
    "Qatar",
    "Oman",
    "Jordan",
    "Mauritania",
]
