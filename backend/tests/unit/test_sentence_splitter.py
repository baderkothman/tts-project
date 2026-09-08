from __future__ import annotations

from backend.app.services.sentence_splitter import split_sentences


def test_empty_and_whitespace_only_return_empty_list():
    assert split_sentences("") == []
    assert split_sentences("   \n  ") == []


def test_single_sentence_no_terminator_is_one_chunk():
    assert split_sentences("مرحبا كيف حالك") == ["مرحبا كيف حالك"]


def test_splits_on_arabic_and_latin_terminators():
    text = "مرحبا. كيف حالك؟ أنا بخير! هل أنت متأكد؛ نعم."
    assert split_sentences(text) == [
        "مرحبا.",
        "كيف حالك؟",
        "أنا بخير!",
        "هل أنت متأكد؛",
        "نعم.",
    ]


def test_splits_on_blank_lines_even_without_terminator():
    text = "السطر الأول\n\nالسطر الثاني"
    assert split_sentences(text) == ["السطر الأول", "السطر الثاني"]


def test_decimal_number_is_not_split():
    # The period in "3.14" is followed by a digit, not whitespace.
    assert split_sentences("السعر هو 3.14 ريال.") == ["السعر هو 3.14 ريال."]


def test_currency_abbreviation_with_internal_period_is_not_split():
    # "د.إ" (dirham) — the period sits between two letters, not before whitespace.
    assert split_sentences("السعر 50 د.إ فقط.") == ["السعر 50 د.إ فقط."]


def test_lone_leftover_punctuation_merges_into_previous_chunk():
    # A standalone terminator separated by whitespace on both sides (e.g.
    # from odd spacing around punctuation) would otherwise become a
    # one-character chunk with nothing worth synthesizing on its own.
    result = split_sentences("مرحبا. ؟ كيف حالك؟")
    assert result == ["مرحبا. ؟", "كيف حالك؟"]


def test_preserves_order_across_many_sentences():
    text = "واحد. اثنان. ثلاثة. أربعة."
    assert split_sentences(text) == ["واحد.", "اثنان.", "ثلاثة.", "أربعة."]
