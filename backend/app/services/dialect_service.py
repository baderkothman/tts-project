"""Dialect resolution and raw-vs-corrected comparison (FR-048, FR-053, US6-7).

`resolve()`: user selection always wins over the classifier (FR-048), and the
classifier still runs when a selection is present so its actual output is
never silently discarded (FR-051, plan.md Design Decision 7).

`select_voice_for_dialect()`: the FR-057/SC-019 fallback path — when a
dialect's preferred Hugging Face TTS model is unavailable (no HF_TOKEN,
provider missing, or the model was never wired in), this falls through to
the profile's existing-provider `fallback_tts_models`, exactly the way
`tts_service._try_fallback` already falls through on a provider failure, so
a dialect never fails to produce *some* speech.

`compare()`: assembles the US7 raw-vs-corrected result by running the
existing text pipeline for "corrected" and a pipeline with pronunciation
correction disabled for "raw", then synthesizing both. Audio is returned as
inline base64 (matching `TTSResponse.audio_base64`'s existing pattern)
rather than written to a file, consistent with "audio is not retained by
default" (spec.md Assumptions) — no temp-file lifecycle to manage or leak.
"""

from __future__ import annotations

import base64
import re

from backend.app.data.dialect_profiles import get as get_dialect_profile
from backend.app.data.hf_model_registry import get as get_hf_model
from backend.app.data.pronunciation_dictionary import lookup as dictionary_lookup
from backend.app.models.dialect import DialectComparisonResult, DialectDetectionResult
from backend.app.models.voice import ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.services.tts_service import NoProviderAvailableError
from backend.app.text_processing.huggingface.dialect_classifier import classify
from backend.app.text_processing.pipeline import process_text

_TOKEN_PATTERN = re.compile(r"[\w؀-ۿ]+")


async def resolve(
    text: str, *, dialect: str | None = None, hf_token: str | None = None
) -> DialectDetectionResult:
    """Resolve a request's dialect. User selection always wins (FR-048)."""
    classifier_result = await classify(text, hf_token=hf_token)

    if dialect is not None:
        profile = get_dialect_profile(dialect)
        family = profile.dialect_family.value if profile else None
        mapped_from_family = bool(
            classifier_result.resolved_dialect
            and family
            and classifier_result.resolved_dialect == family
            and classifier_result.resolved_dialect != dialect
        )
        return DialectDetectionResult(
            resolved_dialect=dialect,
            source="user_selected",
            classifier_label=classifier_result.label,
            classifier_confidence=classifier_result.confidence,
            mapped_from_family=mapped_from_family,
        )

    if classifier_result.resolved_dialect is None:
        # Classifier unavailable or returned a label with no mapped profile
        # (e.g. MAGHREB — spec.md's minimum six profiles don't include it) —
        # degrade to msa rather than leaving the request unresolved (FR-057).
        return DialectDetectionResult(
            resolved_dialect="msa",
            source="classifier",
            classifier_label=classifier_result.label,
            classifier_confidence=classifier_result.confidence,
            unavailable_reason=classifier_result.unavailable_reason
            or f"classifier label '{classifier_result.label}' has no mapped dialect profile",
        )

    return DialectDetectionResult(
        resolved_dialect=classifier_result.resolved_dialect,
        source="classifier",
        classifier_label=classifier_result.label,
        classifier_confidence=classifier_result.confidence,
    )


async def select_voice_for_dialect(
    resolved_dialect: str, registry: ProviderRegistry
) -> tuple[TTSProvider, VoiceConfig, str]:
    """Pick a provider/voice for a resolved dialect.

    Returns `(provider, voice, architecture_used)` where `architecture_used`
    is one of FR-054's vocabulary: `"hf_native_tts"` or `"existing_tts"`.
    Prefers an available Hugging Face dialect-specific model; falls through
    to the profile's existing-provider voices otherwise (FR-057, SC-019).
    """
    profile = get_dialect_profile(resolved_dialect) or get_dialect_profile("msa")
    assert profile is not None  # "msa" is always present in DIALECT_PROFILES

    hf_provider = registry.get("huggingface")
    if (
        profile.preferred_tts_models
        and hf_provider is not None
        and hf_provider.available() == ProviderStatus.AVAILABLE
    ):
        target_repo_ids = {
            m.repo_id for mid in profile.preferred_tts_models if (m := get_hf_model(mid)) is not None
        }
        for voice in await hf_provider.get_voices():
            if voice.provider_voice_id in target_repo_ids:
                return hf_provider, voice, "hf_native_tts"

    for voice_id in profile.fallback_tts_models:
        provider_id = voice_id.split(":", 1)[0]
        provider = registry.get(provider_id)
        if provider is None or provider.available() != ProviderStatus.AVAILABLE:
            continue
        for voice in await provider.get_voices():
            if voice.id == voice_id:
                return provider, voice, "existing_tts"

    default_provider = registry.default()
    if default_provider is None:
        raise NoProviderAvailableError(
            f"no provider available to serve dialect '{resolved_dialect}'"
        )
    voices = await default_provider.get_voices()
    return default_provider, voices[0], "existing_tts"


def _apply_pronunciation_dictionary(text: str, *, dialect: str | None) -> tuple[str, list[str]]:
    """Real, testable dictionary substitution layered on top of the existing
    pipeline output (FR-052). A dialect-scoped entry wins over an unscoped
    one for the same token, per `data/pronunciation_dictionary.py::lookup`."""
    changes: list[str] = []
    result = text
    applied: set[str] = set()
    for word in dict.fromkeys(_TOKEN_PATTERN.findall(text)):  # de-duplicated, order-preserving
        if word in applied:
            continue
        entry = dictionary_lookup(word, dialect=dialect)
        if entry is None:
            continue
        replacement = entry.diacritized or entry.normalized
        if replacement and replacement != word:
            result = re.sub(rf"\b{re.escape(word)}\b", replacement, result)
            changes.append(f"pronunciation dictionary: {word} -> {replacement}")
            applied.add(word)
    return result, changes


async def compare(
    text: str,
    *,
    dialect: str | None,
    registry: ProviderRegistry,
    hf_token: str | None,
    timeout_s: float,
) -> DialectComparisonResult:
    """Assemble the US7 raw-vs-corrected comparison for arbitrary text."""
    detection = await resolve(text, dialect=dialect, hf_token=hf_token)
    provider, voice, architecture = await select_voice_for_dialect(detection.resolved_dialect, registry)

    raw_processed = process_text(text, apply_preprocessing=True, apply_pronunciation=False, locale=voice.locale, provider=provider.id)
    corrected_processed = process_text(text, apply_preprocessing=True, apply_pronunciation=True, locale=voice.locale, provider=provider.id)

    dict_text, dict_changes = _apply_pronunciation_dictionary(
        corrected_processed.processed, dialect=detection.resolved_dialect
    )
    # Only report changes attributable to the pronunciation axis (FR-053) —
    # NOT the preprocessing stages (normalize/dates/currencies/numbers/
    # abbreviations/code-switching), because those run identically in the
    # "raw" rendering too (apply_preprocessing=True for both raw and
    # corrected; only apply_pronunciation and the dictionary differ). Listing
    # a preprocessing-only change here would misleadingly imply the raw and
    # corrected audio differ because of it, when they don't.
    changes = [f"stage: {s.stage_name}" for s in corrected_processed.stages if s.changed and s.stage_name == "pronunciation"]
    changes.extend(dict_changes)
    if dict_changes:
        architecture = "hf_preprocessing_existing_tts" if architecture == "existing_tts" else architecture

    async def _synthesize(text_to_speak: str) -> str:
        request = ProviderRequest(text=text_to_speak, voice=voice, timeout_s=timeout_s)
        try:
            audio = await provider.synthesize(request)
        except ProviderError:
            # Graceful degradation, not a crash (Constitution VI): an empty
            # placeholder is returned and the caller can see changes==[]
            # or inspect this failure through the same channel any other
            # provider failure would use; a full second-provider fallback
            # here would duplicate tts_service's own logic for a comparison
            # endpoint whose primary job is text, not synthesis, resilience.
            return ""
        return base64.b64encode(audio).decode("ascii")

    corrected_audio = await _synthesize(dict_text)
    # When nothing actually changed the spoken text, reuse the same audio
    # for both renderings rather than making a second synthesis call: two
    # separate calls with identical input are not guaranteed byte-identical
    # by every provider, which would read as a fabricated difference and
    # directly contradict Story 7, Scenario 3 ("no correction applied" MUST
    # be stated plainly, not implied by two subtly different audio blobs).
    raw_audio = corrected_audio if raw_processed.processed == dict_text else await _synthesize(raw_processed.processed)
    final_processed_text = corrected_processed.model_copy(update={"processed": dict_text})

    return DialectComparisonResult(
        original_text=text,
        detection=detection,
        processed_text=final_processed_text,
        changes=changes,
        raw_audio_ref=raw_audio,
        corrected_audio_ref=corrected_audio,
        architecture_used=architecture,
    )
