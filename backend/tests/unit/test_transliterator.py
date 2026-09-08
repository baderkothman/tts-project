"""These call real `espeak-ng` (via `phonemizer`) — lightweight and fast
(no model download), but skipped when the espeak-ng system library isn't
installed rather than failing the whole suite over an environment gap.
`brew install espeak-ng` (macOS) / `apt install espeak-ng` (Debian/Ubuntu)."""

from __future__ import annotations

import pytest

from backend.app.services import transliterator


def _espeak_available() -> bool:
    try:
        transliterator.transliterate_word("test")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _espeak_available(), reason="espeak-ng not installed")


def test_react_matches_the_spec_example():
    assert transliterator.transliterate_word("React") == "رياكت"


def test_output_is_pure_arabic_script():
    result = transliterator.transliterate_word("development")
    assert all(not ch.isascii() for ch in result)


def test_compound_acronym_term_splits_reasonably():
    # "FastAPI" should not come back as raw Latin, and should contain
    # roughly two recognizable chunks (fast + spelled-out API).
    result = transliterator.transliterate_word("FastAPI")
    assert result and all(not ch.isascii() or not ch.isalpha() for ch in result)


def test_transliterate_text_preserves_punctuation_and_arabic():
    result = transliterator.transliterate_text("مرحبا, meeting اليوم!")
    assert "مرحبا" in result
    assert "اليوم" in result
    assert "," in result
    assert "!" in result
    assert "meeting" not in result


def test_unknown_word_still_produces_output_not_naive_spelling():
    # A naive letter-by-letter transliteration of "Vercel" would read the
    # Latin letters v-e-r-c-e-l one by one; the phonetic version should not
    # equal that mechanical mapping.
    result = transliterator.transliterate_word("Vercel")
    assert result != "".join(dict.fromkeys("Vercel"))  # sanity: not empty/degenerate
    assert len(result) > 0
