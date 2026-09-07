"""Grapheme-to-phoneme conversion via a registered Hugging Face model (FR-052).

Currently degrades to unavailable for every call: research.md R11's G2P
candidate (`charsiu/g2p_multilingual_byT5_tiny_16_layers_100`) has an
unconfirmed license and is therefore `enabled=False` (FR-058) — same
structural readiness note as `diacritizer.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.app.text_processing.huggingface.model_registry import first_enabled

_INFERENCE_API = "https://router.huggingface.co/hf-inference/models"
# CharsiuG2P expects an ISO-639-based language-code prefix per word
# (research.md R11); Modern Standard Arabic is "ara".
_LANGUAGE_PREFIX = "<ara>:"


@dataclass
class G2PResult:
    phonemes: str | None = None
    unavailable_reason: str | None = None


async def phonemize(token: str, *, hf_token: str | None, timeout_s: float = 10.0) -> G2PResult:
    model = first_enabled("g2p")
    if model is None:
        return G2PResult(unavailable_reason="no g2p model enabled in the registry (research.md R11)")
    if not hf_token:
        return G2PResult(unavailable_reason="HF_TOKEN not configured")

    url = f"{_INFERENCE_API}/{model.repo_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": f"{_LANGUAGE_PREFIX}{token}"}

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError:
        return G2PResult(unavailable_reason="Hugging Face Inference API unreachable")

    if resp.status_code != 200:
        return G2PResult(unavailable_reason=f"Hugging Face returned {resp.status_code}")

    try:
        data = resp.json()
        phonemes = data[0]["generated_text"] if isinstance(data, list) else data["generated_text"]
    except (KeyError, IndexError, TypeError):
        return G2PResult(unavailable_reason="Hugging Face returned an unrecognized response shape")

    return G2PResult(phonemes=phonemes)
