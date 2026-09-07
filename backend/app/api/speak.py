"""GET /api/voices, POST /api/speak (contracts/http-api.md)."""

from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException

from backend.app.config import get_settings
from backend.app.models.speech import SpeechRequest, SpeechResponse
from backend.app.models.voice import Voice
from backend.app.providers.base import ProviderError
from backend.app.providers.groq import GroqProvider
from backend.app.services.latency import LatencyTrace
from backend.app.services.voice_resolution import VoiceResolutionError, resolve_voice

router = APIRouter(prefix="/api", tags=["speak"])


def _get_provider() -> GroqProvider:
    settings = get_settings()
    return GroqProvider(api_key=settings.groq_api_key)


@router.get("/voices", response_model=list[Voice])
async def get_voices() -> list[Voice]:
    provider = _get_provider()
    return await provider.list_voices()


@router.post("/speak", response_model=SpeechResponse)
async def speak(request: SpeechRequest) -> SpeechResponse:
    provider = _get_provider()
    voices = await provider.list_voices()

    try:
        voice = resolve_voice(voices, voice_id=request.voice_id, gender=request.gender)
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "valid_alternatives": exc.valid_alternatives},
        ) from exc

    settings = get_settings()
    trace = LatencyTrace()
    trace.mark_provider_call_started()
    try:
        audio = await provider.synthesize(request.text, voice, timeout_s=settings.request_timeout_s)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=f"[{exc.kind}] {exc.message}") from exc
    trace.mark_audio_received()

    return SpeechResponse(
        audio_base64=base64.b64encode(audio).decode("ascii"),
        content_type="audio/wave",
        voice=voice,
        latency=trace.report(audio),
    )
