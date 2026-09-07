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
import time

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from backend.app.config import get_settings
from backend.app.data.dialects import DIALECTS, Dialect
from backend.app.data.voice_design import AGE_OPTIONS, GENDER_OPTIONS, PITCH_OPTIONS
from backend.app.models.tts import (
    HealthResponse,
    LatencyInfo,
    ModelCapabilities,
    ModelInfo,
    TTSRequest,
    TTSResponse,
)
from backend.app.services.audio import duration_ms, encode_wav
from backend.app.services.inference import ArchitectureName, BaseModelName, InferenceError

router = APIRouter(prefix="/api", tags=["tts"])

_ERROR_STATUS = {
    "not_loaded": 503,
    "invalid_input": 400,
    "generation_failed": 502,
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
        ),
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
        "age_options": AGE_OPTIONS,
        "note": (
            "This model has no fixed speaker roster. Choose a gender/pitch/age combination "
            "(voice design) or upload a short reference clip (voice cloning) instead."
        ),
    }


@router.post("/tts", response_model=TTSResponse)
async def synthesize(
    request: Request,
    text: str = Form(...),
    mode: str = Form("voice_design"),
    dialect_id: str = Form("msa"),
    gender: str | None = Form(None),
    pitch: str = Form("moderate pitch"),
    age: str | None = Form(None),
    whisper: bool = Form(False),
    ref_text: str | None = Form(None),
    speed: float = Form(1.0),
    quality: str = Form("high"),
    guidance_scale: float = Form(2.0),
    ref_audio: UploadFile | None = File(None),
) -> TTSResponse:
    engine = request.app.state.engine
    settings = get_settings()

    try:
        tts_request = TTSRequest(
            text=text,
            mode=mode,  # type: ignore[arg-type]
            dialect_id=dialect_id,
            gender=gender,  # type: ignore[arg-type]
            pitch=pitch,  # type: ignore[arg-type]
            age=age,  # type: ignore[arg-type]
            whisper=whisper,
            ref_text=ref_text,
            speed=speed,
            quality=quality,  # type: ignore[arg-type]
            guidance_scale=guidance_scale,
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

    t0_generation = time.perf_counter()
    try:
        result = await engine.generate(tts_request, ref_audio_bytes=ref_audio_bytes)
    except InferenceError as exc:
        raise HTTPException(status_code=_ERROR_STATUS[exc.kind], detail=exc.message) from exc
    generation_ms = (time.perf_counter() - t0_generation) * 1000.0

    audio_ms = duration_ms(result.samples, result.sample_rate)
    wav_bytes = encode_wav(result.samples, result.sample_rate)

    return TTSResponse(
        audio_base64=base64.b64encode(wav_bytes).decode("ascii"),
        sample_rate=result.sample_rate,
        mode=tts_request.mode,
        dialect_id=tts_request.dialect_id if tts_request.mode != "clone" else None,
        gender=tts_request.gender if tts_request.mode == "voice_design" else None,
        latency=LatencyInfo(
            generation_ms=generation_ms,
            audio_duration_ms=audio_ms,
            real_time_factor=(generation_ms / audio_ms) if audio_ms > 0 else 0.0,
        ),
        warnings=result.warnings,
    )
