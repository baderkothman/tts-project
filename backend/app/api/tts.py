"""GET /api/health, /api/model-info, /api/dialects, /api/voices, POST /api/tts.

There is no `voices` roster: `oddadmix/lahgtna-omnivoice-v2` has no named,
enumerable speaker identities (verified by reading the `omnivoice` package —
voice identity comes from either a free-form `instruct` description or a
cloned reference clip, never a fixed speaker table). `GET /api/voices`
still exists, per the task's suggested API shape, but reports that honestly
instead of inventing a roster of imaginary named voices.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.app.config import get_settings
from backend.app.data.dialects import DIALECTS, Dialect
from backend.app.data.voice_design import GENDER_OPTIONS, PITCH_OPTIONS
from backend.app.models.tts import (
    HealthResponse,
    LatencyInfo,
    ModelCapabilities,
    ModelInfo,
    PreprocessRequest,
    PreprocessResponse,
    SegmentInfo,
    TTSRequest,
    TTSResponse,
)
from backend.app.services import dialect_rewriter, text_preprocessor
from backend.app.services.audio import duration_ms, encode_wav
from backend.app.services.dialect_rewriter import DialectRewriteError
from backend.app.services.inference import ArchitectureName, BaseModelName, InferenceError

router = APIRouter(prefix="/api", tags=["tts"])

# Shared by InferenceError and DialectRewriteError — both are (kind,
# message) exceptions, so one table maps either's `.kind` to a status code.
_ERROR_STATUS = {
    "not_loaded": 503,
    "invalid_input": 400,
    "generation_failed": 502,
    "not_configured": 503,
    "upstream_error": 502,
}


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    engine = request.app.state.engine
    if engine.loaded:
        return HealthResponse(status="ok", model_loaded=True, device=engine.device)
    if engine.load_error:
        return HealthResponse(status="error", model_loaded=False, detail=engine.load_error)
    return HealthResponse(status="loading", model_loaded=False)


@router.get("/model-info", response_model=ModelInfo)
async def model_info(request: Request) -> ModelInfo:
    engine = request.app.state.engine
    settings = get_settings()
    if not engine.loaded:
        raise HTTPException(status_code=503, detail="Model is not loaded yet — check /api/health")

    from backend.app.services import diacritizer, english_tts

    return ModelInfo(
        repo_id=settings.model_repo_id,
        architecture=ArchitectureName,
        base_model=BaseModelName,
        device=engine.device or "unknown",
        sample_rate=engine.sample_rate,
        dialects_supported=len(DIALECTS),
        capabilities=ModelCapabilities(
            voice_design=True,
            voice_cloning=True,
            dialect_control=True,
            diacritics_aware=True,
            named_voice_roster=False,
            automatic_diacritization=True,
            mixed_language_support=True,
        ),
        pipeline_modes=["native", "dual_model", "transliteration"],
        diacritizer_loaded=diacritizer.is_loaded(),
        english_tts_loaded=english_tts.is_loaded(),
        dialect_rewriter_configured=dialect_rewriter.is_configured(),
    )


@router.get("/dialects", response_model=list[Dialect])
async def dialects() -> list[Dialect]:
    return DIALECTS


@router.get("/voices")
async def voices() -> dict:
    """Honest capability report in place of a fabricated named-voice list."""
    return {
        "supports_named_voices": False,
        "supports_voice_design": True,
        "supports_voice_cloning": True,
        "gender_options": GENDER_OPTIONS,
        "pitch_options": PITCH_OPTIONS,
        "note": (
            "This model has no fixed speaker roster. Choose a gender/pitch combination "
            "(voice design) or upload a short reference clip (voice cloning) instead."
        ),
    }


def _segment_infos(segments) -> list[SegmentInfo]:
    return [
        SegmentInfo(language=s.language, original_text=s.original_text, speak_text=s.speak_text, diacritized=s.diacritized)
        for s in segments
    ]


@router.post("/preprocess", response_model=PreprocessResponse)
async def preprocess(body: PreprocessRequest) -> PreprocessResponse:
    """Text-only "what will actually be spoken" preview — no audio, no GPU
    call beyond the (cached) diacritizer, so the UI can show this live as
    the user types without waiting on a full generation.

    When `ai_dialect_rewrite` is set, this also calls OpenAI (see
    `dialect_rewriter.py`) before previewing — so the live preview matches
    what `/api/tts` will actually speak, at the cost of one OpenAI call per
    debounced keystroke pause while the toggle is on."""
    try:
        working_text, rewrite_warnings = await dialect_rewriter.maybe_rewrite(
            body.text, dialect_id=body.dialect_id, enabled=body.ai_dialect_rewrite, gender=body.gender
        )
    except DialectRewriteError as exc:
        raise HTTPException(status_code=_ERROR_STATUS[exc.kind], detail=exc.message) from exc

    result = text_preprocessor.preprocess(
        working_text, dialect_id=body.dialect_id, pipeline_mode=body.pipeline_mode
    )
    return PreprocessResponse(
        original_text=result.original_text,
        processed_text=result.processed_text,
        segments=_segment_infos(result.segments),
        warnings=rewrite_warnings + result.warnings,
    )


async def _build_request(
    *,
    text: str,
    mode: str,
    pipeline_mode: str,
    dialect_id: str,
    gender: str | None,
    pitch: str,
    ref_text: str | None,
    speed: float,
    quality: str,
    guidance_scale: float,
    ref_audio: UploadFile | None,
    ai_dialect_rewrite: bool = False,
) -> tuple[TTSRequest, bytes | None]:
    """Shared by `/tts` and `/tts/stream`: build+validate the typed request
    and read/validate the optional reference-audio upload. Kept as one
    function so the two endpoints can't drift on validation rules."""
    settings = get_settings()
    try:
        tts_request = TTSRequest(
            text=text,
            mode=mode,  # type: ignore[arg-type]
            pipeline_mode=pipeline_mode,  # type: ignore[arg-type]
            dialect_id=dialect_id,
            gender=gender,  # type: ignore[arg-type]
            pitch=pitch,  # type: ignore[arg-type]
            ref_text=ref_text,
            speed=speed,
            quality=quality,  # type: ignore[arg-type]
            guidance_scale=guidance_scale,
            ai_dialect_rewrite=ai_dialect_rewrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ref_audio_bytes: bytes | None = None
    if ref_audio is not None:
        if ref_audio.content_type not in settings.allowed_reference_audio_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported reference audio type '{ref_audio.content_type}'",
            )
        ref_audio_bytes = await ref_audio.read()
        if len(ref_audio_bytes) > settings.max_reference_audio_bytes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Reference audio exceeds the {settings.max_reference_audio_bytes // (1024 * 1024)}MB limit"
                ),
            )

    if tts_request.mode == "clone" and not ref_audio_bytes:
        raise HTTPException(status_code=400, detail="Voice cloning mode requires a reference audio file")

    return tts_request, ref_audio_bytes


@router.post("/tts", response_model=TTSResponse)
async def synthesize(
    request: Request,
    text: str = Form(...),
    mode: str = Form("voice_design"),
    pipeline_mode: str = Form("native"),
    dialect_id: str = Form("msa"),
    gender: str | None = Form(None),
    pitch: str = Form("moderate pitch"),
    ref_text: str | None = Form(None),
    speed: float = Form(1.0),
    quality: str = Form("high"),
    guidance_scale: float = Form(2.0),
    ref_audio: UploadFile | None = File(None),
    ai_dialect_rewrite: bool = Form(False),
) -> TTSResponse:
    pipeline = request.app.state.pipeline
    tts_request, ref_audio_bytes = await _build_request(
        text=text,
        mode=mode,
        pipeline_mode=pipeline_mode,
        dialect_id=dialect_id,
        gender=gender,
        pitch=pitch,
        ref_text=ref_text,
        speed=speed,
        quality=quality,
        guidance_scale=guidance_scale,
        ref_audio=ref_audio,
        ai_dialect_rewrite=ai_dialect_rewrite,
    )

    t0_generation = time.perf_counter()
    try:
        result = await pipeline.synthesize(tts_request, ref_audio_bytes=ref_audio_bytes)
    except (InferenceError, DialectRewriteError) as exc:
        raise HTTPException(status_code=_ERROR_STATUS[exc.kind], detail=exc.message) from exc
    generation_ms = (time.perf_counter() - t0_generation) * 1000.0

    audio_ms = duration_ms(result.samples, result.sample_rate)
    wav_bytes = encode_wav(result.samples, result.sample_rate)
    preview = result.preview

    return TTSResponse(
        audio_base64=base64.b64encode(wav_bytes).decode("ascii"),
        sample_rate=result.sample_rate,
        mode=tts_request.mode,
        pipeline_mode=tts_request.pipeline_mode,
        dialect_id=tts_request.dialect_id if tts_request.mode != "clone" else None,
        gender=tts_request.gender if tts_request.mode == "voice_design" else None,
        latency=LatencyInfo(
            generation_ms=generation_ms,
            audio_duration_ms=audio_ms,
            real_time_factor=(generation_ms / audio_ms) if audio_ms > 0 else 0.0,
        ),
        processed_text=preview.processed_text if preview else tts_request.text,
        segments=_segment_infos(preview.segments) if preview else [],
        warnings=result.warnings,
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_events(pipeline, tts_request: TTSRequest, ref_audio_bytes: bytes | None) -> AsyncIterator[str]:
    """Server-Sent Events body for `/tts/stream`. One `chunk` event per
    sentence as soon as its audio is ready (each carries its own
    `elapsed_ms` since the request started — the first chunk's is this
    endpoint's whole reason to exist: a real time-to-first-audio number,
    not the whole-clip latency `/tts` reports), then one closing `done`
    event with the aggregate stats a benchmark actually wants to log."""
    t0 = time.perf_counter()
    ttfa_ms: float | None = None
    chunk_count = 0
    total_audio_ms = 0.0
    all_warnings: list[str] = []
    try:
        async for chunk in pipeline.synthesize_stream(tts_request, ref_audio_bytes=ref_audio_bytes):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if ttfa_ms is None:
                ttfa_ms = elapsed_ms
            chunk_count += 1
            audio_ms = duration_ms(chunk.samples, chunk.sample_rate)
            total_audio_ms += audio_ms
            all_warnings.extend(chunk.warnings)
            wav_bytes = encode_wav(chunk.samples, chunk.sample_rate)
            yield _sse(
                "chunk",
                {
                    "chunk_index": chunk.index,
                    "chunk_text": chunk.text,
                    "audio_base64": base64.b64encode(wav_bytes).decode("ascii"),
                    "content_type": "audio/wav",
                    "sample_rate": chunk.sample_rate,
                    "audio_duration_ms": audio_ms,
                    "elapsed_ms": elapsed_ms,
                    "is_final": chunk.is_final,
                    "warnings": chunk.warnings,
                },
            )
    except (InferenceError, DialectRewriteError) as exc:
        yield _sse("error", {"kind": exc.kind, "message": exc.message})
        return

    total_ms = (time.perf_counter() - t0) * 1000.0
    yield _sse(
        "done",
        {
            "chunk_count": chunk_count,
            "ttfa_ms": ttfa_ms,
            "total_ms": total_ms,
            "total_audio_duration_ms": total_audio_ms,
            "real_time_factor": (total_ms / total_audio_ms) if total_audio_ms > 0 else 0.0,
            "warnings": all_warnings,
        },
    )


@router.post("/tts/stream")
async def synthesize_stream(
    request: Request,
    text: str = Form(...),
    mode: str = Form("voice_design"),
    pipeline_mode: str = Form("native"),
    dialect_id: str = Form("msa"),
    gender: str | None = Form(None),
    pitch: str = Form("moderate pitch"),
    ref_text: str | None = Form(None),
    speed: float = Form(1.0),
    quality: str = Form("high"),
    guidance_scale: float = Form(2.0),
    ref_audio: UploadFile | None = File(None),
    ai_dialect_rewrite: bool = Form(False),
) -> StreamingResponse:
    """Sentence-chunked variant of `/tts` — same request shape, but returns
    audio as Server-Sent Events, one `chunk` per sentence, so a client (or
    `scripts/benchmark_tts.py`) can measure real time-to-first-audio instead
    of only whole-clip latency. See `SpeechPipeline.synthesize_stream` and
    `sentence_splitter.py` for why this is chunked by sentence rather than
    truly token-streamed (the underlying model has no streaming API)."""
    pipeline = request.app.state.pipeline
    tts_request, ref_audio_bytes = await _build_request(
        text=text,
        mode=mode,
        pipeline_mode=pipeline_mode,
        dialect_id=dialect_id,
        gender=gender,
        pitch=pitch,
        ref_text=ref_text,
        speed=speed,
        quality=quality,
        guidance_scale=guidance_scale,
        ref_audio=ref_audio,
        ai_dialect_rewrite=ai_dialect_rewrite,
    )
    return StreamingResponse(
        _stream_events(pipeline, tts_request, ref_audio_bytes),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
