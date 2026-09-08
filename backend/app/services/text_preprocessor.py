"""Orchestrates one text -> pronunciation-ready-text pass: pronunciation
overrides, light normalization, Arabic/English segmentation, per-segment
Arabic number verbalization + diacritization, and (in `transliteration`
pipeline mode only) English->Arabic-script conversion.

This module produces *text*, not audio — `speech_pipeline.py` decides how
to turn its output into sound depending on `pipeline_mode`. Keeping the two
concerns apart is what lets the same preprocessing result back both the
`/api/preprocess` preview (instant, no model load needed beyond the
diacritizer) and the real `/api/tts` generation call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from backend.app.data.dialects import DIALECT_BY_ID
from backend.app.services import diacritizer, pronunciation_dictionary, transliterator
from backend.app.services.language_segmenter import Segment, segment_languages

PipelineMode = Literal["native", "dual_model", "transliteration"]

# Tatweel (ـ, U+0640) is pure elongation with no pronunciation of its own —
# safe to drop, unlike the letter-folding Constitution III forbids (hamza
# forms, taa marbuta, alif maqsura are never touched here).
_TATWEEL_RE = re.compile("ـ")
_WHITESPACE_RE = re.compile(r"[ \t]+")

# Bare digits (Western 0-9 or Arabic-Indic ٠-٩), so "2345" and "٢٣٤٥" both verbalize.
_NUMBER_RE = re.compile(r"[0-9٠-٩]+")
_ARABIC_INDIC_TO_WESTERN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


@dataclass
class SegmentPreview:
    language: Literal["ar", "en"]
    original_text: str
    speak_text: str
    diacritized: bool = False


@dataclass
class PreprocessResult:
    original_text: str
    processed_text: str
    segments: list[SegmentPreview] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    text = _TATWEEL_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _verbalize_numbers(text: str) -> str:
    from num2words import num2words

    def _replace(match: re.Match[str]) -> str:
        digits = match.group(0).translate(_ARABIC_INDIC_TO_WESTERN)
        try:
            return num2words(int(digits), lang="ar")
        except (ValueError, OverflowError):
            return match.group(0)  # leave anything num2words can't handle as-is

    return _NUMBER_RE.sub(_replace, text)


def _process_arabic_segment(seg: Segment, dialect_id: str) -> SegmentPreview:
    verbalized = _verbalize_numbers(seg.text)
    diacritized_text, applied = diacritizer.diacritize(verbalized, dialect_id=dialect_id)
    return SegmentPreview(language="ar", original_text=seg.text, speak_text=diacritized_text, diacritized=applied)


def _process_english_segment(seg: Segment, mode: PipelineMode) -> SegmentPreview:
    if mode == "transliteration":
        return SegmentPreview(language="en", original_text=seg.text, speak_text=transliterator.transliterate_text(seg.text))
    # native: this text stays embedded in the single Arabic-model call as-is.
    # dual_model: this text is sent to english_tts.py separately; the
    # "speak_text" shown in the preview is still just the English itself.
    return SegmentPreview(language="en", original_text=seg.text, speak_text=seg.text)


@lru_cache(maxsize=256)
def preprocess(text: str, *, dialect_id: str, pipeline_mode: PipelineMode) -> PreprocessResult:
    warnings: list[str] = []

    with_overrides = pronunciation_dictionary.apply_overrides(text)
    normalized = _normalize(with_overrides)

    segments = [
        _process_arabic_segment(seg, dialect_id) if seg.language == "ar" else _process_english_segment(seg, pipeline_mode)
        for seg in segment_languages(normalized)
    ]

    dialect = DIALECT_BY_ID.get(dialect_id)
    if dialect and dialect.written_only:
        warnings.append(
            f"'{dialect.name_en}' has no distinct model parameter in this build; "
            "relying on the dialectal Arabic you typed rather than a language code."
        )
    if pipeline_mode == "dual_model" and any(s.language == "en" for s in segments):
        from backend.app.services import english_tts

        if not english_tts.is_loaded():
            warnings.append(
                english_tts.load_error()
                or "English TTS is still loading — English segments will fall back to native handling for this request."
            )

    processed_text = "".join(s.speak_text for s in segments)
    return PreprocessResult(original_text=text, processed_text=processed_text, segments=segments, warnings=warnings)
