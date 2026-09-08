"""The Arabic dialect catalogue this app actually exposes.

Source of truth, in order of precedence:

1. `oddadmix/lahgtna-omnivoice-v2`'s own model card roadmap
   (https://huggingface.co/oddadmix/lahgtna-omnivoice-v2) — the fine-tune's
   *own* claim of which dialects are "completed" versus merely "planned".
   The roadmap's six planned dialects (UAE, Kuwait, Qatar, Oman, Jordan,
   Mauritania) are deliberately NOT exposed — a roadmap entry is not a
   shipped capability.
2. The underlying `omnivoice` package's language resolver
   (`omnivoice.utils.lang_map.LANG_NAME_TO_ID`, inspected directly from the
   installed package source, not guessed), which is what
   `OmniVoice.generate(..., language=...)` actually accepts. This maps each
   dialect name to the ISO 639-3-ish code OmniVoice's base multilingual
   training used.

Of the 13 dialects Lahgtna's own card marks "completed", 4 are removed here
rather than exposed with a caveat — real user feedback that they "don't
work" in practice, not just an academic gap:

- **Palestinian, Lebanese, Syrian** had no dialect-specific code at all —
  the underlying language map only has one shared code for Levantine Arabic
  (`apc`), so all three resolved to the exact same conditioning. Selecting
  any of the three did nothing to distinguish it from the others.
- **Yemeni** has no language code in the installed package whatsoever
  (verified by reading `omnivoice/utils/lang_map.py` directly — every other
  entry in this table exists there character-for-character). Passing an
  unrecognized language string silently falls back to language-agnostic
  mode (`_resolve_language` in `omnivoice/models/omnivoice.py`), so the
  option produced no real dialect conditioning at all.

`Dialect.written_only` (below) is the mechanism that flagged these — kept
in the model for any future dialect that ends up in the same situation, but
nothing currently exposed uses it: every remaining dialect has its own
distinct, verified language code.
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
# invented. Palestinian, Lebanese, Syrian, and Yemeni are deliberately
# absent — see module docstring and REMOVED_UNRELIABLE_DIALECTS below.
DIALECTS: list[Dialect] = [
    Dialect(id="egyptian", name_en="Egyptian", name_ar="مصرية", language_code="arz"),
    Dialect(id="saudi", name_en="Saudi (Najdi)", name_ar="سعودية (نجدية)", language_code="ars"),
    Dialect(id="moroccan", name_en="Moroccan", name_ar="مغربية", language_code="ary"),
    Dialect(id="iraqi", name_en="Iraqi", name_ar="عراقية", language_code="acm"),
    Dialect(id="sudanese", name_en="Sudanese", name_ar="سودانية", language_code="apd"),
    Dialect(id="libyan", name_en="Libyan", name_ar="ليبية", language_code="ayl"),
    Dialect(id="tunisian", name_en="Tunisian", name_ar="تونسية", language_code="aeb"),
    Dialect(id="bahraini", name_en="Bahraini", name_ar="بحرينية", language_code="abv"),
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

# The model card marks these 4 "completed," and this app shipped them
# briefly, but they were removed after real user feedback that they don't
# work — see module docstring for exactly why (shared/missing language
# codes, no real dialect conditioning). Listed here for the same
# traceability reason as PLANNED_NOT_IMPLEMENTED, above.
REMOVED_UNRELIABLE_DIALECTS = ["Palestinian", "Lebanese", "Syrian", "Yemeni"]
