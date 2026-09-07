"""The Arabic evaluation sample set (FR-038, FR-038a).

Each difficult-content sample carries its expected transformation so SC-003
can be asserted per sample rather than judged by eye.
"""

from __future__ import annotations

from backend.app.models.benchmark import ArabicSample

SAMPLES: list[ArabicSample] = [
    ArabicSample(
        id="msa-1", category="msa", locale="ar-SA",
        text="التعليم هو الأساس لبناء مجتمع متقدم ومزدهر.",
        description="Formal MSA sentence, no special content.",
    ),
    ArabicSample(
        id="msa-2", category="msa", locale="ar-SA",
        text="أعلنت الشركة عن نتائجها المالية للربع الأخير من العام.",
        description="Formal MSA business sentence.",
    ),
    ArabicSample(
        id="dialect-egyptian-1", category="dialect", locale="ar-EG",
        text="إزيك عامل إيه النهاردة؟ أنا رايح الشغل بدري.",
        description="Egyptian Arabic colloquial greeting.",
    ),
    ArabicSample(
        id="dialect-gulf-1", category="dialect", locale="ar-AE",
        text="شلونك اليوم؟ أبغى أروح السوق بعد شوي.",
        description="Gulf Arabic colloquial sentence.",
    ),
    ArabicSample(
        id="pronunciation-1", category="pronunciation", locale="ar-SA",
        text="طلب العلم فريضة على كل مسلم ومسلمة.",
        description="Contains the targeted ambiguous word 'علم'.",
        expected_contains=["عِلْم"],
    ),
    ArabicSample(
        id="numbers-1", category="numbers", locale="ar-SA",
        text="لدينا 125 موظفاً و1,250 عميلاً و25.5 بالمئة نمو و75% رضا.",
        description="Cardinals, grouped thousands, decimals, percentages.",
        expected_behavior="all digits verbalized as Arabic words",
        expected_contains=["مئة وخمسة وعشرون", "بالمئة"],
        expected_absent=["125", "%"],
    ),
    ArabicSample(
        id="dates-1", category="dates", locale="ar-SA",
        text="الاجتماع يوم 27/09/2026 والموعد النهائي 2026-09-27.",
        description="Slash and ISO date formats.",
        expected_contains=["سبتمبر"],
        expected_absent=["/", "2026-09-27"],
    ),
    ArabicSample(
        id="currencies-1", category="currencies", locale="ar-SA",
        text="السعر $25 أو 25 USD أو 100 ريال أو 1,250.50 دولار.",
        description="Symbol, code, and Arabic-name currency forms.",
        expected_contains=["دولار", "ريال", "سنت"],
        expected_absent=["$", "USD"],
    ),
    ArabicSample(
        id="abbreviations-1", category="abbreviations", locale="ar-SA",
        text="د. أحمد م. سارة يعملان في شركة API وAWS وAI.",
        description="Arabic and Latin abbreviations.",
        expected_contains=["دكتور", "مهندس"],
    ),
    ArabicSample(
        id="code-switching-1", category="code_switching", locale="ar-SA",
        text="اليوم عندنا meeting مع فريق الـ AI الساعة 3 PM.",
        description="Arabic/English code-switching.",
        expected_contains=["meeting"],
    ),
    ArabicSample(
        id="emotion-1", category="emotion", locale="ar-SA",
        text="أهلاً وسهلاً بكم في هذا العرض التوضيحي.",
        description="Neutral base sentence for style-comparison rendering.",
    ),
]


def samples_by_category(category: str) -> list[ArabicSample]:
    return [s for s in SAMPLES if s.category == category]
