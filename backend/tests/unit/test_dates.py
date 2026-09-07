"""Date verbalization (FR-010)."""

from backend.app.text_processing.dates import verbalize_dates


def test_slash_date():
    result = verbalize_dates("27/09/2026")
    assert "سبتمبر" in result
    assert "/" not in result


def test_iso_date():
    result = verbalize_dates("2026-09-27")
    assert "سبتمبر" in result
    assert "-" not in result


def test_mixed_format_date():
    result = verbalize_dates("27 سبتمبر 2026")
    assert "سبعة وعشرون" in result
    assert "ألفان وستة وعشرون" in result


def test_date_preceded_by_no_space_conjunction():
    # "و" (and) commonly attaches with no space; Arabic letters are `\w`
    # under Python's default Unicode regex, so a naive `\b` pattern would
    # find no boundary here. Real bug caught during implementation.
    result = verbalize_dates("التاريخ و27/09/2026")
    assert "سبتمبر" in result
    assert "27" not in result
