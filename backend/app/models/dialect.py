"""Dialect and Hugging Face model-registry types (US6-7, FR-048-FR-062).

Additive to `models/voice.py`'s `Dialect` enum (the five-way locale-routing
family) and `models/tts.py`'s `PronunciationRule` (pattern-matched rewriter):
a `DialectProfile.id` may be *narrower* than a `Dialect` value (e.g.
``lebanese`` vs. the routing-level ``levantine``), representing what a real
classifier can and cannot distinguish honestly (FR-051), and
`PronunciationDictionaryEntry` is looked up by exact/aliased token rather
than pattern-matched. See data-model.md for the full field-by-field contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.models.tts import ProcessedText
from backend.app.models.voice import Dialect


class DialectProfile(BaseModel):
    """Dialect identity metadata used to route a resolved dialect (FR-049)."""

    id: str
    name: str
    region: str | None = None
    # The `Dialect` enum value this profile maps to for existing
    # Edge/Groq/ElevenLabs voice routing (bridges the finer HF-level
    # granularity to the coarser provider-voice-routing granularity).
    dialect_family: Dialect
    locale: str | None = None
    aliases: list[str] = Field(default_factory=list)
    # References into the pronunciation dictionary/rule set. MUST NOT include
    # a rule that rewrites this dialect's vocabulary toward MSA (FR-050) —
    # reviewed the same way PronunciationRule.whole_word prevents substring
    # corruption: a data defect, not a runtime decision.
    normalization_rules: list[str] = Field(default_factory=list)
    pronunciation_model: str | None = None  # an HFModelConfig.id
    diacritization_model: str | None = None  # an HFModelConfig.id
    preferred_tts_models: list[str] = Field(default_factory=list)  # HFModelConfig.id(s)
    # Existing provider/voice ids (Edge/Groq/ElevenLabs) used when no HF
    # model applies or is unavailable (FR-049, FR-057).
    fallback_tts_models: list[str] = Field(default_factory=list)


class PronunciationDictionaryEntry(BaseModel):
    """A token-level pronunciation record, looked up by exact/aliased token.

    Distinct from `PronunciationRule` (models/tts.py), which is
    pattern-matched: this is a closed-set lookup for names, places, products,
    and other tokens research would otherwise have to enumerate as patterns.
    """

    token: str
    dialect: str | None = None  # a DialectProfile.id; None applies everywhere
    normalized: str | None = None
    diacritized: str | None = None
    phonemes: str | None = None
    aliases: list[str] = Field(default_factory=list)
    notes: str | None = None


class HFModelConfig(BaseModel):
    """A model-registry record (FR-055, FR-058).

    An entry with ``license is None`` or ``enabled is False`` MUST NOT be
    selected by any HF-consuming service — this is what makes "don't
    download before verifying" (FR-058) mechanical rather than a process
    reminder.
    """

    id: str
    repo_id: str
    task: Literal["dialect_tts", "dialect_classification", "diacritization", "g2p"]
    dialects: list[str] = Field(default_factory=list)  # DialectProfile.id values
    local_supported: bool = False
    remote_supported: bool = True
    streaming: bool = False
    requires_gpu: bool = False
    approximate_vram_gb: float | None = None
    license: str | None = None
    enabled: bool = False
    source_url: str
    notes: str = ""


class DialectDetectionResult(BaseModel):
    """The outcome of resolving a request's dialect (FR-048, FR-051)."""

    resolved_dialect: str  # a DialectProfile.id
    source: Literal["user_selected", "classifier"]
    # Populated even when overridden by user selection, for transparency
    # (Story 6, Scenario 4) — never discarded silently.
    classifier_label: str | None = None
    classifier_confidence: float | None = None
    # True when resolved_dialect is narrower than what the classifier could
    # actually distinguish (e.g. app prefers "lebanese", classifier only
    # resolves "levantine").
    mapped_from_family: bool = False
    # Populated when detection could not run at all (no HF_TOKEN, model
    # unavailable, timeout) so the caller can state plainly why, per
    # FR-057/SC-019, instead of silently defaulting.
    unavailable_reason: str | None = None


class DialectComparisonResult(BaseModel):
    """US7 response shape: raw-vs-corrected comparison for arbitrary text."""

    original_text: str
    detection: DialectDetectionResult
    processed_text: ProcessedText
    changes: list[str] = Field(default_factory=list)
    raw_audio_ref: str
    corrected_audio_ref: str
    # Which of FR-054's four architectures produced corrected_audio_ref, for
    # traceability back to the evaluation (research.md, docs/DIALECT_EVALUATION.md).
    architecture_used: str
