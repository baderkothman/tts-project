"""Unit tests for the diacritizer's own logic — the real ByT5 model is
never loaded here (see backend/tests/integration/test_live_model.py for
that); `_run_model` is monkeypatched so these stay fast and offline."""

from __future__ import annotations

import pytest

from backend.app.services import diacritizer


def test_has_diacritics_detects_fatha():
    assert diacritizer.has_diacritics("مَرْحَبًا")


def test_has_diacritics_false_for_plain_text():
    assert not diacritizer.has_diacritics("مرحبا")


def test_strip_word_final_irab_keeps_stem_vowels():
    # "نَرُوحُ" -> drop only the trailing damma (the case ending); the stem
    # vowels on ن and ر must survive.
    assert diacritizer._strip_word_final_irab("نَرُوحُ") == "نَرُوح"


def test_strip_word_final_irab_preserves_shadda():
    # Real reproduced case: shadda is gemination, not a case ending, and
    # must never be stripped even when it's the last mark on the word.
    assert diacritizer._strip_word_final_irab("عَمَّ") == "عَمَّ"


def test_strip_word_final_irab_strips_tanween():
    # Real reproduced bug: the model added a genitive tanween to a
    # colloquial verb ("go") that isn't inflected that way in speech.
    assert diacritizer._strip_word_final_irab("رُوحٍ") == "رُوح"


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
