"""Synthesis endpoints: /api/tts, /api/tts/stream, /api/preview.

Per contracts/http-api.md: validation and voice resolution happen BEFORE any
byte is written on the streaming path, because a stream's status is committed
with the first byte.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.models.tts import ProcessedText, TTSRequest, TTSResponse
from backend.app.providers.base import ProviderError
from backend.app.providers.registry import get_registry
from backend.app.services.latency import LatencyTrace
from backend.app.services.tts_service import (
    NoProviderAvailableError,
    build_plan,
    stream_synthesis,
    synthesize_complete,
)
from backend.app.services.voice_router import VoiceResolutionError
from backend.app.text_processing.pipeline import process_text

router = APIRouter(prefix="/api", tags=["tts"])


@router.post("/preview", response_model=ProcessedText)
async def preview(request: TTSRequest) -> ProcessedText:
    """Processed text without synthesis — no provider call, works with zero
    credentials (FR-015)."""
    return process_text(
        request.text,
        apply_preprocessing=request.apply_preprocessing,
        apply_pronunciation=request.apply_pronunciation,
        locale=request.locale,
        provider=request.provider,
    )


@router.post("/tts", response_model=TTSResponse)
async def synthesize(request: TTSRequest) -> TTSResponse:
    registry = get_registry()
    trace = LatencyTrace(client_t0_ms=request.client_t0_ms)
    try:
        return await synthesize_complete(registry, request, trace)
    except NoProviderAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=400, detail={"message": str(exc), "valid_alternatives": exc.valid_alternatives}
        ) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc


@router.post("/tts/stream")
async def synthesize_stream(request: TTSRequest, http_request: Request) -> StreamingResponse:
    registry = get_registry()
    trace = LatencyTrace(client_t0_ms=request.client_t0_ms)

    # All validation and voice resolution happen before the first byte is
    # written, since the HTTP status is committed with it (contracts/http-api.md).
    try:
        plan = await build_plan(registry, request, trace)
    except NoProviderAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=400, detail={"message": str(exc), "valid_alternatives": exc.valid_alternatives}
        ) from exc

    async def _generate():
        try:
            async for chunk in stream_synthesis(registry, plan, trace):
                if await http_request.is_disconnected():
                    # Client disconnected mid-stream: stop consuming provider
                    # quota promptly rather than continuing (edge case).
                    break
                yield chunk
        except ProviderError:
            return  # status already committed; truncation signals failure

    headers = {
        "X-TTS-Provider": plan.provider.id,
        "X-TTS-Voice": plan.voice.id,
        "X-TTS-Used-Fallback": str(plan.used_fallback).lower(),
        "X-TTS-Emotion-Native": str(plan.emotion_native).lower(),
    }
    return StreamingResponse(
        _generate(), media_type=request.output_format.content_type, headers=headers
    )
