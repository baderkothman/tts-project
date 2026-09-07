"""Diacritization (tashkeel) via a registered Hugging Face model (FR-052, FR-053).

Currently degrades to unavailable for every call: the one `diacritization`
candidate research.md R11 found (`Abdou/arabic-tashkeel-flan-t5-small`) has
an unconfirmed license and is therefore `enabled=False` in the registry
(FR-058) — this module is structurally ready to call it the moment that is
confirmed and the entry is enabled, without any change to its own code or
its callers.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.text_processing.huggingface.model_registry import first_enabled

_INFERENCE_API = "https://router.huggingface.co/hf-inference/models"


@dataclass
class DiacritizationResult:
    diacritized: str | None = None
    unavailable_reason: str | None = None


async def diacritize(text: str, *, hf_token: str | None, timeout_s: float = 10.0) -> DiacritizationResult:
    model = first_enabled("diacritization")
    if model is None:
        return DiacritizationResult(
            unavailable_reason="no diacritization model enabled in the registry (research.md R11)"
        )
    if not hf_token:
        return DiacritizationResult(unavailable_reason="HF_TOKEN not configured")

    url = f"{_INFERENCE_API}/{model.repo_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json={"inputs": text}, headers=headers)
    except httpx.HTTPError:
        return DiacritizationResult(unavailable_reason="Hugging Face Inference API unreachable")

    if resp.status_code != 200:
        return DiacritizationResult(unavailable_reason=f"Hugging Face returned {resp.status_code}")

    try:
        data = resp.json()
        text_out = data[0]["generated_text"] if isinstance(data, list) else data["generated_text"]
    except (KeyError, IndexError, TypeError):
        return DiacritizationResult(unavailable_reason="Hugging Face returned an unrecognized response shape")

    return DiacritizationResult(diacritized=text_out)
