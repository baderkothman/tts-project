"""Synthesis orchestration: route -> preprocess -> synthesize (FR-031, FR-033).

On a retryable ProviderError, attempts the fallback provider and marks the
response so a substituted result is never mistaken for a primary one
(FR-033). A provider failure never crashes the service (FR-034).
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass

from backend.app.models.tts import ProcessedText, TTSRequest, TTSResponse
from backend.app.models.voice import VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.services.latency import LatencyTrace
from backend.app.services.voice_router import VoiceResolutionError, resolve_voice
from backend.app.text_processing.pipeline import process_text


class NoProviderAvailableError(Exception):
    pass


@dataclass
class SynthesisPlan:
    """The resolved, ready-to-execute request: provider, voice, and processed
    text, computed once and shared by the streaming and non-streaming paths so
    they cannot drift (plan.md design decision #4)."""

    provider: TTSProvider
    voice: VoiceConfig
    processed: ProcessedText
    provider_request: ProviderRequest
    emotion_native: bool
    used_fallback: bool = False
    fallback_reason: str | None = None


async def build_plan(
    registry: ProviderRegistry, request: TTSRequest, trace: LatencyTrace
) -> SynthesisPlan:
    provider = registry.get(request.provider) if request.provider else registry.default()
    if provider is None:
        raise NoProviderAvailableError(
            "no TTS provider is available; configure credentials or use 'edge'"
        )

    voices = await provider.get_voices()
    try:
        voice = resolve_voice(
            provider, voices, voice_id=request.voice_id, locale=request.locale, dialect=request.dialect
        )
    except VoiceResolutionError:
        raise

    processed = process_text(
        request.text,
        apply_preprocessing=request.apply_preprocessing,
        apply_pronunciation=request.apply_pronunciation,
        locale=voice.locale,
        provider=provider.id,
    )
    trace.mark("T2")

    caps = provider.capabilities()
    provider_request = ProviderRequest(
        text=processed.processed,
        voice=voice,
        emotion=request.emotion,
        speaking_rate=request.speaking_rate,
        pitch=request.pitch,
        output_format=request.output_format,
        # Single source of truth: the registry's own settings, not a
        # separately imported global — a request must be timed out per the
        # configuration of the registry that actually serves it (FR-032).
        timeout_s=registry.settings.tts_request_timeout_s,
    )
    emotion_native = caps.native_emotions

    return SynthesisPlan(
        provider=provider,
        voice=voice,
        processed=processed,
        provider_request=provider_request,
        emotion_native=emotion_native,
    )


async def _try_fallback(
    registry: ProviderRegistry, plan: SynthesisPlan, reason: str
) -> SynthesisPlan:
    fallback = registry.fallback()
    if fallback is None or fallback.id == plan.provider.id:
        raise NoProviderAvailableError(f"primary failed ({reason}) and no fallback is available")

    voices = await fallback.get_voices()
    try:
        voice = resolve_voice(fallback, voices, locale=plan.voice.locale)
    except VoiceResolutionError:
        voice = voices[0]

    new_request = plan.provider_request.model_copy(update={"voice": voice})
    plan.provider = fallback
    plan.voice = voice
    plan.provider_request = new_request
    plan.used_fallback = True
    plan.fallback_reason = reason
    return plan


async def stream_synthesis(
    registry: ProviderRegistry, plan: SynthesisPlan, trace: LatencyTrace
) -> AsyncIterator[bytes]:
    """Stream audio, falling back to an alternative provider on failure.

    Fallback is only safe BEFORE any byte has reached the client: once
    audio has been sent, a stream's content is effectively committed, and
    appending a different provider's (or voice's) audio afterward would
    produce corrupted, mixed-voice output rather than a clean substitution.
    So a failure after the first byte terminates the stream instead of
    triggering a fallback — the client detects truncation, matching
    contracts/http-api.md. This was caught by a fallback test failing on
    concatenated chunk counts during implementation (Constitution V).
    """
    trace.mark("T3")
    any_byte_sent = False
    try:
        async for chunk in plan.provider.stream(plan.provider_request):
            if not any_byte_sent:
                trace.mark("T4")
                any_byte_sent = True
            trace.audio_bytes += len(chunk)
            yield chunk
    except ProviderError as exc:
        if exc.retryable and not any_byte_sent:
            plan = await _try_fallback(registry, plan, exc.message)
            trace.mark("T3")
            async for chunk in plan.provider.stream(plan.provider_request):
                if not any_byte_sent:
                    trace.mark("T4")
                    any_byte_sent = True
                trace.audio_bytes += len(chunk)
                yield chunk
        else:
            raise
    trace.mark("T7")


async def synthesize_complete(
    registry: ProviderRegistry, request: TTSRequest, trace: LatencyTrace
) -> TTSResponse:
    plan = await build_plan(registry, request, trace)
    chunks = bytearray()
    async for chunk in stream_synthesis(registry, plan, trace):
        chunks.extend(chunk)
        trace.mark("T5")

    latency = trace.report()
    return TTSResponse(
        audio_base64=base64.b64encode(bytes(chunks)).decode("ascii"),
        content_type=request.output_format.content_type,
        processed_text=plan.processed,
        voice=plan.voice,
        provider=plan.provider.id,
        emotion_applied=request.emotion,
        emotion_native=plan.emotion_native,
        used_fallback=plan.used_fallback,
        fallback_reason=plan.fallback_reason,
        latency=latency,
        audio_duration_ms=latency.audio_duration_ms,
    )
