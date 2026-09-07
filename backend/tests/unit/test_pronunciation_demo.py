"""Corrected and uncorrected paths differ from identical source (FR-020)."""

from backend.app.text_processing.dictionary import PRONUNCIATION_DEMO
from backend.app.text_processing.pipeline import process_text


def test_demo_has_required_provenance_fields():
    assert PRONUNCIATION_DEMO.provider_observed
    assert PRONUNCIATION_DEMO.voice_observed


def test_uncorrected_and_corrected_differ():
    without = process_text(
        PRONUNCIATION_DEMO.original_text, apply_pronunciation=False
    )
    with_correction = process_text(
        PRONUNCIATION_DEMO.original_text, apply_pronunciation=True
    )
    assert without.processed != with_correction.processed


def test_corrected_matches_recorded_correction():
    result = process_text(PRONUNCIATION_DEMO.original_text, apply_pronunciation=True)
    assert result.processed == PRONUNCIATION_DEMO.corrected_text
