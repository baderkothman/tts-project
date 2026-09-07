"""Pronunciation rule application (FR-017), incl. whole-word boundary (CHK022)."""

from backend.app.text_processing.pronunciation import apply_pronunciation_rules


def test_definite_article_clitic_still_corrected():
    # "العلم" carries the "ال" (definite article) clitic; the rule strips it,
    # corrects the root, and reattaches the prefix unchanged.
    result = apply_pronunciation_rules("طلب العلم فريضة")
    assert "العِلْم" in result


def test_rule_does_not_fire_inside_longer_word():
    # "معلم" (teacher) contains "علم" as a substring but is a different word;
    # the whole-word boundary must prevent the rule from corrupting it.
    result = apply_pronunciation_rules("هو معلم في المدرسة")
    assert result == "هو معلم في المدرسة"


def test_bare_word_is_corrected():
    result = apply_pronunciation_rules("عندي علم بهذا الأمر")
    assert "عِلْم" in result


def test_brand_name_respelled():
    result = apply_pronunciation_rules("استخدم ChatGPT اليوم")
    assert "ChatGPT" not in result
    assert "تشات" in result
