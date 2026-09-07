"""Local MPS/CPU execution backend (research.md R10).

Refuses to load any `HFModelConfig` not marked `local_supported` — this
enforces the 24GB-unified-memory Apple Silicon ceiling measured in R10 in
code, not only as registry data a caller could ignore. `torch`/`transformers`
are imported lazily inside the function bodies, not at module level, so this
module can be imported (e.g. by the provider adapter's type checks) without
requiring the optional `huggingface-local` extra to be installed.
"""

from __future__ import annotations

import asyncio

from backend.app.providers.base import ProviderError
from backend.app.providers.huggingface.models import HFSynthesisRequest, HFSynthesisResult

_PROVIDER_ID = "huggingface"


async def synthesize(request: HFSynthesisRequest) -> HFSynthesisResult:
    if not request.model.local_supported:
        raise ProviderError(
            _PROVIDER_ID, "unavailable",
            f"{request.model.id} is not marked local_supported "
            "(research.md R10 hardware ceiling) — use the hosted Inference API instead",
        )

    try:
        import torch  # noqa: F401
        from transformers import pipeline  # noqa: F401
    except ImportError as exc:
        raise ProviderError(
            _PROVIDER_ID, "unavailable",
            "Local Hugging Face execution requires the 'huggingface-local' extra "
            "(pip install -e '.[huggingface-local]') — not installed",
        ) from exc

    def _run() -> bytes:
        # A real local pipeline is intentionally not wired further than this:
        # per research.md R12, the hosted Inference API is the default and
        # verified path; local execution is documented and structurally
        # ready (this backend, the local_supported gate, the optional
        # dependency) but no model has yet been confirmed to justify the
        # added complexity of a bespoke local inference call per task
        # (Constitution VIII — simplest sufficient design).
        raise NotImplementedError(
            "Local backend is structurally present but not yet wired to a "
            "specific model pipeline — no candidate has required it over the "
            "hosted Inference API default (research.md R12)"
        )

    try:
        return HFSynthesisResult(audio_bytes=await asyncio.to_thread(_run))
    except NotImplementedError as exc:
        raise ProviderError(_PROVIDER_ID, "unavailable", str(exc)) from exc
