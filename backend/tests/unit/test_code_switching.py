"""Code-switching handling (FR-013)."""

from backend.app.text_processing.code_switching import handle_code_switching


def test_mixed_sentence_preserves_both_languages():
    text = "اليوم عندنا meeting مع فريق الـ AI الساعة 3 PM."
    result = handle_code_switching(text)
    assert "meeting" in result
    assert "اليوم" in result


def test_latin_run_gets_spacing():
    result = handle_code_switching("عندناmeeting اليوم")
    assert "عندنا meeting" in result
