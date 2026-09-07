"""Normalizer preserves meaning-bearing distinctions (FR-006, FR-007, FR-008)."""

from backend.app.text_processing.arabic_normalizer import normalize


def test_hamza_forms_preserved():
    # These are different words; folding them is a meaning change.
    assert "أسف" in normalize("أسف")
    assert "آسف" in normalize("آسف")
    assert "إسف" not in normalize("أسف")  # not silently converted


def test_taa_marbuta_preserved():
    assert normalize("مدرسة") == "مدرسة"
    assert "مدرسه" not in normalize("مدرسة")


def test_alif_maqsura_preserved():
    assert normalize("على") == "على"
    assert normalize("علي") == "علي"
    assert normalize("على") != normalize("علي")


def test_diacritics_preserved():
    diacritized = "عِلْم"
    assert normalize(diacritized) == diacritized


def test_tatweel_removed():
    assert "ـ" not in normalize("مرحـــبا")


def test_arabic_indic_digits_converted():
    assert normalize("١٢٣") == "123"


def test_invisible_characters_removed():
    zwsp = "​"
    assert zwsp not in normalize(f"مرحبا{zwsp}بك")
