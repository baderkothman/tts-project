"""Text-in dialect detection (FR-048, research.md R13).

Calls the registry's enabled `dialect_classification` model (currently
`IbrahimAmin/marbertv2-arabic-written-dialect-classifier`, research.md R11)
via the Hugging Face hosted Inference API. Uses raw `httpx` rather than the
`huggingface_hub` SDK so this module — outside `providers/` — never imports a
tracked provider SDK (`test_import_boundaries.py`); the REST contract is
simple enough (`POST .../models/{repo_id}`, JSON body/response) that no SDK
convenience is lost.

Degrades to an unavailable result on any failure — never raises outward
(FR-057). Callers (`services/dialect_service.py`) treat "classifier ran but
returned nothing" as a normal, reportable state, not an exception.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.text_processing.huggingface.model_registry import first_enabled

_INFERENCE_API = "https://router.huggingface.co/hf-inference/models"

# The classifier's own output labels (research.md R11: MARBERTv2 5-way
# classifier) mapped to this project's DialectProfile ids. MAGHREB has no
# corresponding DialectProfile yet (spec.md's minimum six do not include it)
# — dialect_service.py degrades that case explicitly rather than pretending
# a profile exists.
LABEL_TO_PROFILE: dict[str, str] = {
    "MSA": "msa",
    "GLF": "gulf",
    "EGY": "egyptian",
    "LEV": "levantine",
    "MAGHREB": "maghrebi",
}


@dataclass
class ClassifierResult:
    label: str | None = None  # raw classifier label, e.g. "LEV"
    resolved_dialect: str | None = None  # LABEL_TO_PROFILE.get(label)
    confidence: float | None = None
    unavailable_reason: str | None = None


async def classify(text: str, *, hf_token: str | None, timeout_s: float = 10.0) -> ClassifierResult:
    if not hf_token:
        return ClassifierResult(unavailable_reason="HF_TOKEN not configured")

    model = first_enabled("dialect_classification")
    if model is None:
        return ClassifierResult(unavailable_reason="no dialect_classification model enabled in the registry")

    url = f"{_INFERENCE_API}/{model.repo_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json={"inputs": text}, headers=headers)
    except httpx.TimeoutException:
        return ClassifierResult(unavailable_reason="Hugging Face dialect classifier request timed out")
    except httpx.HTTPError:
        return ClassifierResult(unavailable_reason="Hugging Face Inference API unreachable")

    if resp.status_code == 503:
        return ClassifierResult(unavailable_reason="Hugging Face model is cold-starting")
    if resp.status_code == 401:
        return ClassifierResult(unavailable_reason="Hugging Face rejected the token")
    if resp.status_code != 200:
        return ClassifierResult(unavailable_reason=f"Hugging Face returned {resp.status_code}")

    try:
        data = resp.json()
        # text-classification pipeline responses are typically a list of
        # {label, score} dicts (possibly nested one level for batched input).
        predictions = data[0] if data and isinstance(data[0], list) else data
        best = max(predictions, key=lambda p: p["score"])
        label = str(best["label"]).upper()
        confidence = float(best["score"])
    except (KeyError, ValueError, IndexError, TypeError):
        return ClassifierResult(unavailable_reason="Hugging Face returned an unrecognized response shape")

    return ClassifierResult(
        label=label,
        resolved_dialect=LABEL_TO_PROFILE.get(label),
        confidence=confidence,
    )
