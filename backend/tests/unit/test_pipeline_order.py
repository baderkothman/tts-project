"""Stage order matters (plan.md design decision #1)."""

from backend.app.text_processing.pipeline import process_text


def test_date_digits_not_consumed_by_numbers_stage():
    result = process_text("الموعد 27/09/2026")
    assert "سبتمبر" in result.processed


def test_currency_amount_not_consumed_by_numbers_stage():
    result = process_text("الإجمالي 1,250.50 دولار")
    assert "دولار" in result.processed
    assert "سنت" in result.processed


def test_pronunciation_runs_last_and_can_override():
    result = process_text("عندي علم بهذا")
    assert "عِلْم" in result.processed
