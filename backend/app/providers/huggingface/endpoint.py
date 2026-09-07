"""Dedicated Hugging Face Inference Endpoint backend (research.md R12 —
documented, not implemented by default: no candidate model in the Model
Evaluation Matrix has demonstrated a need to pay for a warm, dedicated
endpoint over the free hosted Inference API).

Structurally present so FR-056's "at least two execution modes" is backed by
real code for the two modes actually used (hosted API, local) plus a clear,
non-crashing stub for the third that a future engineer can complete by
supplying an endpoint URL — never a silent no-op.
"""

from __future__ import annotations

from backend.app.providers.base import ProviderError
from backend.app.providers.huggingface.models import HFSynthesisRequest, HFSynthesisResult

_PROVIDER_ID = "huggingface"


async def synthesize(request: HFSynthesisRequest) -> HFSynthesisResult:
    raise ProviderError(
        _PROVIDER_ID, "unavailable",
        "Dedicated Hugging Face Inference Endpoint is not configured for any "
        "model in this prototype (research.md R12) — use the hosted "
        "Inference API or local execution instead",
    )
