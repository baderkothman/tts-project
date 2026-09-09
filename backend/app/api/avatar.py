"""POST /api/tts/avatar and the job endpoints around it — the Talking
Avatar feature's API surface.

Long-running work never blocks one open HTTP request (the brief's own
explicit requirement): `POST /api/tts/avatar` validates its inputs
synchronously (fast — portrait decode + face detection, no model call) and
returns `202 Accepted` with a `job_id` the moment a job is queued. Progress
is then either polled (`GET .../jobs/{id}`) or streamed
(`GET .../jobs/{id}/events`, Server-Sent Events — this app's own existing
pattern for a comparable case, see `api/tts.py`'s `/tts/stream`) rather than
the client having to guess a polling interval.

No authentication/authorization exists anywhere in this app today (verified
directly — there is no user model, no session, no auth middleware in
`main.py` or any router). `job_id` (a random UUID4) is therefore the de
facto access token for a job's media, the same way it would be the only
thing gating access even with auth added later — but there is currently no
check that the caller who created a job is the same one fetching it beyond
"do you know the job_id". Documented as a real, current limitation in
`docs/AVATAR_ARCHITECTURE.md`, not silently glossed over.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from backend.app.config import get_settings
from backend.app.data.emotions import DEFAULT_EMOTION, EMOTION_NAMES
from backend.app.models.avatar import AvatarGenerationRequest, AvatarJobCreateResponse, AvatarJobResponse
from backend.app.services.avatar_jobs import AvatarJob, AvatarJobLimitError, AvatarJobManager
from backend.app.services.portrait_validator import PortraitValidationError, validate_portrait

router = APIRouter(prefix="/api/tts/avatar", tags=["avatar"])

_ERROR_STATUS: dict[str, int] = {
    # AvatarEngineError / job-manager kinds
    "invalid_input": 400,
    "generation_failed": 502,
    "not_available": 503,
    "timeout": 504,
    "internal_error": 500,
    # PortraitValidationError kinds
    "unsupported_format": 415,
    "corrupted": 400,
    "resolution_too_low": 400,
    "file_too_large": 413,
    "no_face": 400,
    "multiple_faces": 400,
    "face_too_small": 400,
}


@router.get("/emotions")
async def emotions() -> dict:
    """Honest capability report, matching `api/tts.py`'s `/api/voices`
    convention — a closed, model-agnostic vocabulary (see
    `data/emotions.py`), not a fabricated per-engine list."""
    return {"emotions": EMOTION_NAMES, "default": DEFAULT_EMOTION}


async def _read_ref_audio(ref_audio: UploadFile | None) -> bytes | None:
    """Same validation `api/tts.py::_build_request` applies to `ref_audio`
    — duplicated rather than imported so this router has no dependency on
    `api/tts.py`'s internals (AGENTS.md: keep services loosely coupled;
    this is ~10 lines, not worth a shared-module refactor for)."""
    if ref_audio is None:
        return None
    settings = get_settings()
    if ref_audio.content_type not in settings.allowed_reference_audio_types:
        raise HTTPException(status_code=400, detail=f"Unsupported reference audio type '{ref_audio.content_type}'")
    data = await ref_audio.read()
    if len(data) > settings.max_reference_audio_bytes:
        raise HTTPException(
            status_code=400, detail=f"Reference audio exceeds the {settings.max_reference_audio_bytes // (1024 * 1024)}MB limit"
        )
    return data


@router.post("", response_model=AvatarJobCreateResponse, status_code=202)
async def create_avatar_job(
    request: Request,
    text: str = Form(...),
    mode: str = Form("voice_design"),
    dialect_id: str = Form("msa"),
    gender: str | None = Form(None),
    pitch: str = Form("moderate pitch"),
    ref_text: str | None = Form(None),
    speed: float = Form(1.0),
    quality: str = Form("high"),
    guidance_scale: float = Form(2.0),
    emotion: str = Form(DEFAULT_EMOTION),
    ai_dialect_rewrite: bool = Form(False),
    portrait: UploadFile = File(...),
    ref_audio: UploadFile | None = File(None),
) -> AvatarJobCreateResponse:
    settings = get_settings()
    manager: AvatarJobManager = request.app.state.avatar_jobs

    try:
        gen_request = AvatarGenerationRequest(
            text=text,
            mode=mode,  # type: ignore[arg-type]
            dialect_id=dialect_id,
            gender=gender,  # type: ignore[arg-type]
            pitch=pitch,  # type: ignore[arg-type]
            ref_text=ref_text,
            speed=speed,
            quality=quality,  # type: ignore[arg-type]
            guidance_scale=guidance_scale,
            emotion=emotion,  # type: ignore[arg-type]
            ai_dialect_rewrite=ai_dialect_rewrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    portrait_bytes = await portrait.read()
    try:
        validated = validate_portrait(
            portrait_bytes, content_type=portrait.content_type or "", max_bytes=settings.max_portrait_bytes
        )
    except PortraitValidationError as exc:
        raise HTTPException(status_code=_ERROR_STATUS[exc.kind], detail=exc.message) from exc

    ref_audio_bytes = await _read_ref_audio(ref_audio)
    if gen_request.mode == "clone" and not ref_audio_bytes:
        raise HTTPException(status_code=400, detail="Voice cloning mode requires a reference audio file")

    try:
        job = manager.create_job(gen_request, portrait=validated, ref_audio_bytes=ref_audio_bytes)
    except AvatarJobLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return AvatarJobCreateResponse(job_id=job.id, status=job.status)


def _to_response(job: AvatarJob) -> AvatarJobResponse:
    base = f"/api/tts/avatar/jobs/{job.id}"
    return AvatarJobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        engine=job.engine_name,
        audio_url=f"{base}/audio" if job.audio_path else None,
        video_url=f"{base}/video" if job.video_path else None,
        duration=job.duration_s,
        processing_time=job.processing_time_s,
        error_kind=job.error_kind,
        error=job.error_message,
        warnings=job.warnings,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _get_job_or_404(request: Request, job_id: str) -> AvatarJob:
    manager: AvatarJobManager = request.app.state.avatar_jobs
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Avatar job not found")
    return job


@router.get("/jobs/{job_id}", response_model=AvatarJobResponse)
async def get_avatar_job(request: Request, job_id: str) -> AvatarJobResponse:
    return _to_response(_get_job_or_404(request, job_id))


@router.post("/jobs/{job_id}/cancel")
async def cancel_avatar_job(request: Request, job_id: str) -> dict:
    manager: AvatarJobManager = request.app.state.avatar_jobs
    _get_job_or_404(request, job_id)
    cancelled = manager.cancel(job_id)
    return {"cancelled": cancelled}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _job_events(manager: AvatarJobManager, job_id: str) -> AsyncIterator[str]:
    from backend.app.models.avatar import TERMINAL_STATUSES

    q = manager.subscribe(job_id)
    try:
        while True:
            event = await q.get()
            yield _sse(event.model_dump())
            if event.status in TERMINAL_STATUSES:
                return
    finally:
        manager.unsubscribe(job_id, q)


@router.get("/jobs/{job_id}/events")
async def avatar_job_events(request: Request, job_id: str) -> StreamingResponse:
    manager: AvatarJobManager = request.app.state.avatar_jobs
    _get_job_or_404(request, job_id)
    return StreamingResponse(
        _job_events(manager, job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/video")
async def get_avatar_video(request: Request, job_id: str) -> FileResponse:
    job = _get_job_or_404(request, job_id)
    if not job.video_path or not job.video_path.exists():
        raise HTTPException(status_code=404, detail="Video not ready")
    return FileResponse(job.video_path, media_type="video/mp4", filename=f"{job_id}.mp4")


@router.get("/jobs/{job_id}/audio")
async def get_avatar_audio(request: Request, job_id: str) -> FileResponse:
    job = _get_job_or_404(request, job_id)
    if not job.audio_path or not job.audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not ready")
    return FileResponse(job.audio_path, media_type="audio/wav", filename=f"{job_id}.wav")
