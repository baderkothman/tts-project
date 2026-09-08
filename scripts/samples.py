"""Shared sample matrix used by both `generate_samples.py` (item 2 — save
real audio + a written gallery) and `benchmark_tts.py` (item 5 — measure
real latency/TTFA on the same texts). Defined once so the two scripts can
never describe different sentences than the ones actually measured/heard.

Covers the requested matrix directly:
MSA, one dialect, difficult names/words, numbers+dates+currency+
abbreviations+English mixed together, and the same sentence spoken with
different voice-design styles.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    id: str
    category: str
    label_ar: str
    text: str
    dialect_id: str = "msa"
    pitch: str = "moderate pitch"
    whisper: bool = False
    gender: str | None = None
    notes: str = ""


SAMPLES: list[Sample] = [
    Sample(
        id="msa_01",
        category="msa",
        label_ar="فصحى قياسية",
        text="التكنولوجيا الحديثة تُغيّر طريقة تواصل الناس مع بعضهم البعض حول العالم.",
        dialect_id="msa",
    ),
    Sample(
        id="dialect_saudi_01",
        category="dialect",
        label_ar="سعودية (نجدية) عامية",
        text="وش عندك اليوم؟ يا ليت تجي نتقهوى شوي عند أبوي بعد صلاة العصر.",
        dialect_id="saudi",
        notes="Colloquial Saudi phrasing the model has no MSA equivalent for ('وش', 'نتقهوى').",
    ),
    Sample(
        id="difficult_names_01",
        category="difficult_words",
        label_ar="أسماء أعلام صعبة",
        text="التقى دوستويفسكي بالمخرج كريشتوف كيشلوفسكي في مهرجان إشبيلية السينمائي.",
        dialect_id="msa",
        notes=(
            "Transliterated foreign proper nouns (Dostoevsky, Krzysztof Kieślowski) — "
            "the classic mispronunciation source item 3 demonstrates fixing via "
            "pronunciation_overrides.json."
        ),
    ),
    Sample(
        id="mixed_content_01",
        category="mixed_content",
        label_ar="أرقام وتواريخ وعملات واختصارات وكلمات إنجليزية",
        text=(
            "اجتمع د. أحمد يوم 15 مارس 2024 الساعة 3:30 مساءً، ودفع 250 ريال سعودي "
            "مقابل اشتراك Netflix عبر تطبيق iPhone الجديد."
        ),
        dialect_id="msa",
        notes="Number, date, time, currency, an honorific abbreviation (د.), two English brand words.",
    ),
]

# Same base sentence, spoken with different voice-design styles. The model
# has no dedicated "emotion" parameter (verified against the installed
# `omnivoice` package's instruct vocabulary — gender/age/pitch/whisper only,
# see README.md), so pitch + whisper are used as the closest real,
# non-fabricated proxy for style/emotion variation.
_STYLE_TEXT = "أنا سعيد جدًا بلقائك اليوم، وأتمنى أن نتعاون قريبًا."

STYLE_VARIANTS: list[Sample] = [
    Sample(
        id="style_neutral",
        category="style_variant",
        label_ar="محايد (نبرة متوسطة)",
        text=_STYLE_TEXT,
        pitch="moderate pitch",
    ),
    Sample(
        id="style_excited",
        category="style_variant",
        label_ar="حماس (نبرة عالية جدًا)",
        text=_STYLE_TEXT,
        pitch="very high pitch",
    ),
    Sample(
        id="style_calm_low",
        category="style_variant",
        label_ar="هدوء (نبرة منخفضة جدًا)",
        text=_STYLE_TEXT,
        pitch="very low pitch",
    ),
    Sample(
        id="style_whisper",
        category="style_variant",
        label_ar="همس",
        text=_STYLE_TEXT,
        pitch="low pitch",
        whisper=True,
    ),
]

ALL_SAMPLES: list[Sample] = SAMPLES + STYLE_VARIANTS
