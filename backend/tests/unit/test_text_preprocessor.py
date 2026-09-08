"""Unit tests for the preprocessing orchestration. `diacritizer.diacritize`
is monkeypatched (a fixed, obviously-fake transform) so these exercise
segmentation/override/warning wiring, not the real model — see
backend/tests/integration/test_live_model.py for the real pipeline."""

from __future__ import annotations

import pytest

from backend.app.data.dialects import Dialect
from backend.app.services import diacritizer, text_preprocessor


@pytest.fixture(autouse=True)
def _fake_diacritizer(monkeypatch):
    def fake(text, *, dialect_id="msa"):
        return f"[{text}]", True  # bracket the input so it's obvious it "ran"

    monkeypatch.setattr(diacritizer, "diacritize", fake)
    text_preprocessor.preprocess.cache_clear()
    yield
    text_preprocessor.preprocess.cache_clear()


def test_pure_arabic_gets_diacritized():
    result = text_preprocessor.preprocess("مرحبا", dialect_id="msa", pipeline_mode="native")
    assert result.segments == [text_preprocessor.SegmentPreview("ar", "مرحبا", "[مرحبا]", True)]
    assert result.processed_text == "[مرحبا]"


def test_native_mode_leaves_english_untouched():
    result = text_preprocessor.preprocess("hello world", dialect_id="msa", pipeline_mode="native")
    assert result.segments[0].language == "en"
    assert result.segments[0].speak_text == "hello world"


def test_transliteration_mode_converts_english():
    result = text_preprocessor.preprocess("hello", dialect_id="msa", pipeline_mode="transliteration")
    seg = result.segments[0]
    assert seg.language == "en"
    assert seg.speak_text != "hello"  # transliterated to Arabic script
    assert all(not ch.isascii() or not ch.isalpha() for ch in seg.speak_text)


def test_mixed_text_produces_ordered_segments():
    result = text_preprocessor.preprocess("مرحبا developer اليوم", dialect_id="msa", pipeline_mode="native")
    languages = [s.language for s in result.segments]
    assert languages == ["ar", "en", "ar"]


def test_written_only_dialect_adds_warning(monkeypatch):
    # No currently-exposed dialect is written_only (the 4 that were —
    # Palestinian/Lebanese/Syrian/Yemeni — were removed entirely; see
    # data/dialects.py) — this synthetic entry keeps the warning mechanism
    # itself covered for whatever future dialect might need it.
    fake_dialect = Dialect(id="fake_written_only", name_en="Fakeish", name_ar="وهمية", language_code=None, written_only=True)
    monkeypatch.setitem(text_preprocessor.DIALECT_BY_ID, "fake_written_only", fake_dialect)
    result = text_preprocessor.preprocess("شلونك", dialect_id="fake_written_only", pipeline_mode="native")
    assert any("Fakeish" in w for w in result.warnings)


def test_msa_dialect_has_no_warning():
    result = text_preprocessor.preprocess("مرحبا", dialect_id="msa", pipeline_mode="native")
    assert result.warnings == []


def test_pronunciation_override_applied_before_segmentation():
    # "OpenAI" is in the real overrides.json shipped with the app —
    # exercising the real file here (not monkeypatched) is deliberate: this
    # is what actually ships.
    result = text_preprocessor.preprocess("جربت OpenAI اليوم", dialect_id="msa", pipeline_mode="native")
    # Once overridden to Arabic script, "OpenAI" is no longer its own
    # English segment — it's part of the surrounding Arabic run.
    languages = [s.language for s in result.segments]
    assert "en" not in languages


def test_number_verbalization_runs_before_diacritization():
    result = text_preprocessor.preprocess("عندي 5 كتب", dialect_id="msa", pipeline_mode="native")
    # The fake diacritizer brackets whatever text it received — if that
    # text still contained a bare digit, num2words didn't run first.
    assert "5" not in result.segments[0].speak_text
