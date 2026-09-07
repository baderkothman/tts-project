"""Currency verbalization (FR-011)."""

from backend.app.text_processing.currencies import verbalize_currencies


def test_dollar_symbol_prefix():
    result = verbalize_currencies("$25")
    assert "دولار" in result
    assert "$" not in result


def test_usd_code_suffix():
    result = verbalize_currencies("25 USD")
    assert "دولار" in result


def test_arabic_riyal_name():
    result = verbalize_currencies("100 ريال")
    assert "ريال" in result
    assert "100" not in result


def test_amount_with_subunit():
    result = verbalize_currencies("1,250.50 دولار")
    assert "دولار" in result
    assert "سنت" in result
    assert "," not in result
