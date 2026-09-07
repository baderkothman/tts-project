"""Abbreviation handling (FR-012)."""

from backend.app.text_processing.abbreviations import verbalize_abbreviations


def test_arabic_abbreviation_expanded():
    assert verbalize_abbreviations("د. أحمد") == "دكتور أحمد"
    assert verbalize_abbreviations("م. سارة") == "مهندس سارة"


def test_latin_initialism_spelled_out():
    result = verbalize_abbreviations("API")
    assert result == "إيه بي آي"


def test_multiple_latin_initialisms():
    result = verbalize_abbreviations("AWS و AI")
    assert "دبليو" in result  # from AWS


def test_latin_initialism_preceded_by_no_space_conjunction():
    result = verbalize_abbreviations("وAPI جديد")
    assert "API" not in result
    assert "إيه" in result
