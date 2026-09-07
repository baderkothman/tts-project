"""Token-level pronunciation dictionary (FR-052).

Closed-set lookup by exact or aliased token — distinct from
`text_processing/dictionary.py`'s pattern-matched `PronunciationRule` data.
Covers the categories FR-052 names: Arabic/Lebanese/Saudi personal names,
place names, organization/product names, technical vocabulary, English
loanwords, and acronyms. `diacritized`/`phonemes` are filled in only where
manually verified here; a `None` value is honest absence, not an omission
(consistent with the project's "never fake precision" discipline).
"""

from __future__ import annotations

from backend.app.models.dialect import PronunciationDictionaryEntry

PRONUNCIATION_DICTIONARY: list[PronunciationDictionaryEntry] = [
    # --- Personal names ---
    PronunciationDictionaryEntry(
        token="خالد",
        normalized="خالد",
        diacritized="خَالِد",
        aliases=["Khaled", "Khalid"],
        notes="Common Arabic given name; undiacritized form is unambiguous but benefits from tashkeel for a non-native reader.",
    ),
    PronunciationDictionaryEntry(
        token="جورج",
        dialect="lebanese",
        normalized="جورج",
        diacritized="جُورج",
        aliases=["George"],
        notes="Common Lebanese Christian given name — an English-derived name spelled in Arabic script.",
    ),
    PronunciationDictionaryEntry(
        token="عبدالعزيز",
        dialect="saudi",
        normalized="عبد العزيز",
        diacritized="عَبْد الْعَزِيز",
        aliases=["Abdulaziz", "Abdul Aziz"],
        notes="Saudi royal-family and common given name; frequently written without the word-separating space, which this entry normalizes.",
    ),
    # --- Place names ---
    PronunciationDictionaryEntry(
        token="بيروت",
        normalized="بيروت",
        diacritized="بَيْرُوت",
        aliases=["Beirut"],
        notes="Capital of Lebanon.",
    ),
    PronunciationDictionaryEntry(
        token="جدة",
        dialect="saudi",
        normalized="جدة",
        diacritized="جِدَّة",
        aliases=["Jeddah", "Jedda"],
        notes="Saudi coastal city; undiacritized form can misread the doubled dal.",
    ),
    PronunciationDictionaryEntry(
        token="الرياض",
        dialect="saudi",
        normalized="الرياض",
        diacritized="الرِّيَاض",
        aliases=["Riyadh"],
        notes="Capital of Saudi Arabia.",
    ),
    # --- Organization / product names ---
    PronunciationDictionaryEntry(
        token="هيوغنغ فيس",
        normalized="Hugging Face",
        phonemes=None,
        aliases=["Hugging Face", "HF"],
        notes="Transliteration of an English product name is not idiomatic Arabic practice — kept in Latin script by the code-switching stage instead; this entry documents the mapping for reference.",
    ),
    # --- Technical vocabulary / English loanwords / acronyms ---
    PronunciationDictionaryEntry(
        token="API",
        normalized="إيه بي آي",
        diacritized="إيه بي آي",
        aliases=["api"],
        notes="Latin initialism read letter-by-letter in Arabic technical speech, matching the existing abbreviations-stage convention.",
    ),
    PronunciationDictionaryEntry(
        token="meeting",
        dialect="lebanese",
        normalized="meeting",
        aliases=["ميتنغ"],
        notes="Common Lebanese/Levantine code-switched English loanword used untranslated in conversational speech (spec.md Story 6 sample).",
    ),
    PronunciationDictionaryEntry(
        token="deploy",
        dialect="lebanese",
        normalized="deploy",
        aliases=["ديبلوي"],
        notes="Common Lebanese tech-conversation code-switched English loanword.",
    ),
]


def lookup(token: str, *, dialect: str | None = None) -> PronunciationDictionaryEntry | None:
    """Exact/aliased lookup. A dialect-scoped entry takes precedence over an
    unscoped one for the same token (edge case, spec.md Edge Cases)."""
    scoped: PronunciationDictionaryEntry | None = None
    unscoped: PronunciationDictionaryEntry | None = None
    for entry in PRONUNCIATION_DICTIONARY:
        if token != entry.token and token not in entry.aliases:
            continue
        if entry.dialect == dialect and dialect is not None:
            scoped = entry
        elif entry.dialect is None:
            unscoped = entry
    return scoped or unscoped
