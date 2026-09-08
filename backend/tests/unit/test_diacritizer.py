"""Unit tests for the diacritizer's own logic — the real ByT5 model is
never loaded here (see backend/tests/integration/test_live_model.py for
that); `_run_model` is monkeypatched so these stay fast and offline."""

from __future__ import annotations

import sys
import types

import pytest

from backend.app.services import diacritizer


def test_has_diacritics_detects_fatha():
    assert diacritizer.has_diacritics("مَرْحَبًا")


def test_has_diacritics_false_for_plain_text():
    assert not diacritizer.has_diacritics("مرحبا")


def test_strip_word_final_irab_keeps_stem_vowels():
    # "نَرُوحُ" -> drop only the trailing damma (the case ending); the stem
    # vowels on ن and ر must survive.
    assert diacritizer.strip_dialectal_case_endings("نَرُوحُ") == "نَرُوح"


def test_strip_word_final_irab_preserves_shadda():
    # Real reproduced case: shadda is gemination, not a case ending, and
    # must never be stripped even when it's the last mark on the word.
    assert diacritizer.strip_dialectal_case_endings("عَمَّ") == "عَمَّ"


def test_strip_word_final_irab_strips_tanween():
    # Real reproduced bug: the model added a genitive tanween to a
    # colloquial verb ("go") that isn't inflected that way in speech.
    assert diacritizer.strip_dialectal_case_endings("رُوحٍ") == "رُوح"


def test_strip_word_final_irab_strips_case_ending_before_trailing_punctuation():
    # Real reproduced case (AI dialect rewrite path): a case-ending vowel
    # right before attached punctuation ("...بِالشِّرْكِةِ.") used to survive
    # because the old regex only matched a diacritic at the literal end of
    # the string — never one followed by a period.
    assert diacritizer.strip_dialectal_case_endings("بِالشِّرْكِةِ.") == "بِالشِّرْكِة."
    assert diacritizer.strip_dialectal_case_endings("اليومُ؟") == "اليوم؟"


def test_diacritize_skips_already_diacritized_text(monkeypatch):
    called = False

    def fail_if_called(text):
        nonlocal called
        called = True
        return text

    monkeypatch.setattr(diacritizer, "_run_model", fail_if_called)
    result, applied = diacritizer.diacritize("مَرْحَبًا", dialect_id="msa")
    assert applied is False
    assert result == "مَرْحَبًا"
    assert called is False


def test_diacritize_applies_model_for_plain_msa(monkeypatch):
    monkeypatch.setattr(diacritizer, "_run_model", lambda text: "مَرْحَبًا")
    result, applied = diacritizer.diacritize("مرحبا", dialect_id="msa")
    assert applied is True
    assert result == "مَرْحَبًا"


def test_diacritize_strips_irab_for_non_msa_dialect(monkeypatch):
    monkeypatch.setattr(diacritizer, "_run_model", lambda text: "نَرُوحُ الْيَوْمَ")
    result, applied = diacritizer.diacritize("نروح اليوم", dialect_id="saudi")
    assert applied is True
    assert result == "نَرُوح الْيَوْم"


def test_diacritize_empty_text_is_a_no_op():
    result, applied = diacritizer.diacritize("   ", dialect_id="msa")
    assert applied is False
    assert result == "   "


def test_diacritize_processes_each_line_independently(monkeypatch):
    # Real reproduced bug: a multi-line segment was fed to `_run_model` as
    # one blob, so one call's fixed generation budget could truncate and
    # silently drop every line after the cutoff. Each line must reach
    # `_run_model` as its own call so one line's output can never consume
    # another line's budget.
    calls: list[str] = []

    def fake_run_model(text: str) -> str:
        calls.append(text)
        return f"[{text}]"

    monkeypatch.setattr(diacritizer, "_run_model", fake_run_model)
    result, applied = diacritizer.diacritize("مرحبا\nكيفك\nشكرا", dialect_id="msa")
    assert applied is True
    assert calls == ["مرحبا", "كيفك", "شكرا"]
    assert result == "[مرحبا]\n[كيفك]\n[شكرا]"


def test_diacritize_preserves_blank_lines_between_content(monkeypatch):
    monkeypatch.setattr(diacritizer, "_run_model", lambda text: f"[{text}]")
    result, applied = diacritizer.diacritize("مرحبا\n\nشكرا", dialect_id="msa")
    assert applied is True
    assert result == "[مرحبا]\n\n[شكرا]"


def test_diacritize_a_diacritized_line_does_not_block_other_lines(monkeypatch):
    # Previously `has_diacritics` gated the *whole* input: one already-
    # diacritized line silently prevented every other line from being
    # diacritized at all.
    monkeypatch.setattr(diacritizer, "_run_model", lambda text: f"[{text}]")
    result, applied = diacritizer.diacritize("مَرْحَبًا\nكيفك", dialect_id="msa")
    assert applied is True
    assert result == "مَرْحَبًا\n[كيفك]"


def test_max_new_tokens_scales_with_input_and_has_a_floor():
    assert diacritizer._max_new_tokens(10) == 512  # floor for short input
    assert diacritizer._max_new_tokens(1000) == 2048  # capped, not 3000
    assert diacritizer._max_new_tokens(200) == 600  # scales for mid-length input


def test_diacritize_degrades_gracefully_when_model_unavailable(monkeypatch):
    # Real reproduced bug (Railway deploy, disk-full diacritizer load):
    # main.py's startup promises a failed diacritizer "degrades gracefully"
    # instead of blocking the app, but a request-time retry propagated the
    # load failure straight into a 500 for every /api/tts call. Text must
    # come back unchanged, not raise.
    def boom(text: str) -> str:
        raise RuntimeError("Diacritizer failed to load")

    monkeypatch.setattr(diacritizer, "_run_model", boom)
    result, applied = diacritizer.diacritize("مرحبا", dialect_id="msa")
    assert applied is False
    assert result == "مرحبا"


def test_diacritize_degrades_gracefully_across_multiple_lines(monkeypatch):
    def boom(text: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(diacritizer, "_run_model", boom)
    result, applied = diacritizer.diacritize("مرحبا\nكيفك", dialect_id="msa")
    assert applied is False
    assert result == "مرحبا\nكيفك"


def test_load_records_error_and_fails_fast_on_retry(monkeypatch):
    """`_load()` must not re-attempt an already-failed (expensive, doomed)
    download on every call — real production case: with no fail-fast check,
    every single /api/tts request retried the same disk-full download."""
    monkeypatch.setattr(diacritizer, "_model", None)
    monkeypatch.setattr(diacritizer, "_tokenizer", None)
    monkeypatch.setattr(diacritizer, "_load_error", None)

    calls = {"count": 0}

    class _FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(_name):
            calls["count"] += 1
            raise OSError("No space left on device")

    class _FakeAutoModel:
        @staticmethod
        def from_pretrained(_name):
            raise AssertionError("should not be reached — tokenizer fails first")

    fake_transformers = types.SimpleNamespace(
        AutoModelForSeq2SeqLM=_FakeAutoModel, AutoTokenizer=_FakeAutoTokenizer
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    with pytest.raises(OSError, match="No space left on device"):
        diacritizer._load()
    assert diacritizer.load_error() == "No space left on device"
    assert calls["count"] == 1

    # Second call: must fail fast with the cached error, not retry.
    with pytest.raises(RuntimeError, match="No space left on device"):
        diacritizer._load()
    assert calls["count"] == 1
