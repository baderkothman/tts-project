from __future__ import annotations

from backend.app.services.language_segmenter import segment_languages


def _as_tuples(segments):
    return [(s.language, s.text) for s in segments]


def test_empty_text_returns_no_segments():
    assert segment_languages("") == []


def test_pure_arabic_is_one_segment():
    assert _as_tuples(segment_languages("مرحبا كيف حالك")) == [("ar", "مرحبا كيف حالك")]


def test_pure_english_is_one_segment():
    assert _as_tuples(segment_languages("hello there")) == [("en", "hello there")]


def test_spec_worked_example():
    # The exact example from the feature brief — surrounding spaces bind to
    # the Arabic neighbor, and "React developer" merges into one run.
    result = _as_tuples(segment_languages("مرحبا React developer كيفك"))
    assert result == [("ar", "مرحبا "), ("en", "React developer"), ("ar", " كيفك")]


def test_consecutive_english_words_merge_into_one_segment():
    result = _as_tuples(segment_languages("اليوم عندي meeting مع الـ development team وبعدها"))
    languages = [lang for lang, _ in result]
    assert languages.count("en") == 2  # "meeting" and "development team" — not split per word


def test_number_inside_arabic_sentence_stays_arabic():
    result = _as_tuples(segment_languages("عندي 5 كتب"))
    assert result == [("ar", "عندي 5 كتب")]


def test_number_inside_english_run_stays_english():
    result = _as_tuples(segment_languages("iPhone 15 Pro"))
    assert result == [("en", "iPhone 15 Pro")]


def test_compound_dotted_and_hyphenated_tokens_stay_intact():
    result = _as_tuples(segment_languages("جرب React.js و GPT-5 اليوم"))
    assert ("en", "React.js") in result
    assert ("en", "GPT-5") in result


def test_url_is_not_split_mid_token():
    result = _as_tuples(segment_languages("زوروا https://example.com/page اليوم"))
    en_segments = [text for lang, text in result if lang == "en"]
    assert any("https://example.com/page" in seg for seg in en_segments)


def test_acronyms_are_english():
    result = _as_tuples(segment_languages("استخدم API و UI و AWS"))
    en_texts = "".join(text for lang, text in result if lang == "en")
    assert "API" in en_texts and "UI" in en_texts and "AWS" in en_texts


def test_bare_numbers_and_punctuation_default_to_arabic():
    assert _as_tuples(segment_languages("42")) == [("ar", "42")]
