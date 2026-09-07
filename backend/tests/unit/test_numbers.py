"""Number verbalization (FR-009, FR-014)."""

from backend.app.text_processing.numbers import integer_to_arabic, verbalize_numbers


def test_cardinals():
    assert integer_to_arabic(0) == "صفر"
    assert integer_to_arabic(1) == "واحد"
    assert integer_to_arabic(21) == "واحد وعشرون"
    assert integer_to_arabic(100) == "مئة"
    assert integer_to_arabic(1000) == "ألف"
    assert integer_to_arabic(2000) == "ألفان"


def test_percent_verbalized():
    result = verbalize_numbers("75%")
    assert "بالمئة" in result
    assert "%" not in result


def test_decimal_verbalized():
    result = verbalize_numbers("25.5")
    assert "فاصلة" in result


def test_grouped_thousands_verbalized():
    result = verbalize_numbers("1,250")
    assert "," not in result
    assert "ألف" in result


def test_identifier_digits_spoken_individually():
    result = verbalize_numbers("+96170123456")
    # A phone number is read digit-by-digit, not as one giant quantity.
    assert "زائد" in result
    assert "تسعة" in result  # first digit of 9,6,1,7,0...


def test_plain_number_not_confused_with_identifier():
    result = verbalize_numbers("125")
    assert "مئة وخمسة وعشرون" == result
