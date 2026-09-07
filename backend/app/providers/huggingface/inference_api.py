"""Hosted Hugging Face Inference API backend (research.md R12 — the default
execution mode: no local download, works within the local hardware ceiling
measured in R10, and matches the credential-gated-but-optional pattern
already proven for Groq/ElevenLabs).

Uses `huggingface_hub`'s `InferenceClient` rather than hand-rolled REST calls
— it is the vendor's own thin, actively maintained client, and its usage is
confined to this one file inside `providers/`, satisfying Constitution II's
"vendor-specific code lives only in adapters" boundary (enforced by
`test_import_boundaries.py`, which tracks `huggingface_hub` as a provider SDK).
"""

from __future__ import annotations

import asyncio

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from backend.app.providers.base import ProviderError
from backend.app.providers.huggingface.models import HFSynthesisRequest, HFSynthesisResult

_PROVIDER_ID = "huggingface"


async def synthesize(request: HFSynthesisRequest) -> HFSynthesisResult:
    """Call the hosted Inference API for a `dialect_tts` model.

    Raises ProviderError, never a `huggingface_hub` exception, per PC-06 —
    even though this backend is not itself a `TTSProvider`, its caller
    (`providers/huggingface/provider.py`) is, and must be able to trust a
    uniform error type.
    """
    if not request.hf_token:
        raise ProviderError(
            _PROVIDER_ID, "auth",
            "Hugging Face token not configured (set HF_TOKEN to enable this capability)",
        )

    # Explicit provider="hf-inference" (Hugging Face's own native serverless
    # backend), not the default "auto" third-party-provider selection —
    # live-discovered (2026-09-07): "auto" raises a bare, unhelpful
    # StopIteration when no third-party provider serves a niche community
    # model, whereas "hf-inference" returns a real, mappable HTTP error
    # (400/410) stating exactly why, which is what the branches below need.
    client = InferenceClient(
        model=request.model.repo_id, provider="hf-inference",
        token=request.hf_token, timeout=request.timeout_s,
    )

    def _call() -> bytes:
        # text_to_speech is synchronous in huggingface_hub; run off the
        # event loop so this coroutine does not block it (Constitution IV).
        return client.text_to_speech(request.text)

    try:
        audio = await asyncio.to_thread(_call)
    except HfHubHTTPError as exc:
        status = getattr(exc.response, "status_code", None) if exc.response is not None else None
        if status == 401:
            raise ProviderError(_PROVIDER_ID, "auth", "Hugging Face rejected the token") from exc
        if status == 429:
            raise ProviderError(
                _PROVIDER_ID, "rate_limit", "Hugging Face Inference API rate limit exceeded"
            ) from exc
        if status == 503:
            # A cold-starting hosted model returns 503 while it loads —
            # treated as retryable/timeout, matching the same fallback path
            # a slow Groq call would take (Constitution VI).
            raise ProviderError(
                _PROVIDER_ID, "timeout",
                "Hugging Face model is cold-starting on the hosted Inference API",
            ) from exc
        if status is not None and status >= 500:
            raise ProviderError(_PROVIDER_ID, "server", f"Hugging Face server error {status}") from exc
        # Include the vendor's own detail (e.g. "Model not supported by
        # provider hf-inference", or a 410 "deprecated and no longer
        # supported") rather than a generic message — live-discovered to be
        # the actual, distinguishing reason for several niche community
        # models (research.md R11/R12 follow-up), not a malformed request.
        raise ProviderError(_PROVIDER_ID, "bad_request", f"Hugging Face rejected the request: {exc}") from exc
    except TimeoutError as exc:
        raise ProviderError(_PROVIDER_ID, "timeout", "Hugging Face Inference API request timed out") from exc
    except StopIteration as exc:
        raise ProviderError(
            _PROVIDER_ID, "unavailable",
            "Hugging Face found no Inference Provider willing to serve this model",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort mapping, never leaks a raw SDK exception
        raise ProviderError(_PROVIDER_ID, "unavailable", "Hugging Face Inference API unreachable") from exc

    return HFSynthesisResult(audio_bytes=audio)
