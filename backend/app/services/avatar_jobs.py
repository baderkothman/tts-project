"""The async job architecture the brief asks for, in place of holding one
HTTP request open for the whole TTS-then-video pipeline.

Deliberately in-process (an `asyncio.Queue` plus a handful of worker
`asyncio.Task`s inside this one FastAPI process), not Redis/Celery/a
separate queue service — this repo has no database, message broker, or
multi-instance deployment story anywhere today (`config.py`/`main.py`
confirm it: one process, in-memory model state, no persistence layer), and
`AGENTS.md` §2's "do not add a framework... when deterministic code...
meets the requirement" cuts directly against introducing three new pieces
of infrastructure for a single-instance deployment. This is a real,
documented trade-off, not an oversight — see `docs/AVATAR_ARCHITECTURE.md`'s
"Why in-process, not Celery/Redis" section for what a horizontally-scaled
deployment would actually need to change.

## Cancellation — the honest scope

A queued job is cancelled outright (never starts). A job already inside
`AvatarEngine.generate()` cannot be interrupted mid-flight: that call runs
real blocking work (`StubAvatarEngine` shells `ffmpeg` from a worker
thread) behind `asyncio.to_thread`, and neither `asyncio.Task.cancel()` nor
`asyncio.wait_for`'s timeout can stop a thread pool worker that is already
running — only unblock the *coroutine waiting on it* once the thread
eventually finishes on its own. So cancelling (or timing out) a job in
`generating_video` is cooperative at the *stage* boundary: the request is
recorded immediately, the job manager stops waiting and reports the job as
cancelled/failed right away, but the abandoned engine call keeps running in
the background until it finishes and its result is simply discarded
(video file deleted, nothing surfaced to the client). This is a structural
limitation of any locally-run subprocess engine, not a bug — a future
remote engine (`hf_jobs_engine.py`) that dispatches a real HF Job gets a
much cleaner mid-flight cancellation point (an actual "cancel this remote
job" API call) once it's implemented.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from backend.app.config import Settings
from backend.app.data.dialects import DIALECT_BY_ID
from backend.app.models.avatar import PROGRESS_BY_STATUS, TERMINAL_STATUSES, AvatarGenerationRequest, AvatarJobStatus
from backend.app.models.tts import TTSRequest
from backend.app.services import tts_cache
from backend.app.services.avatar_engine import AvatarEngine, AvatarEngineError, AvatarOptions, EmotionConfig
from backend.app.services.dialect_rewriter import DialectRewriteError
from backend.app.services.inference import InferenceError
from backend.app.services.portrait_validator import ValidatedPortrait

logger = logging.getLogger("lahgtna.avatar_jobs")


class AvatarJobLimitError(Exception):
    """Raised by `create_job()` when the server is already at capacity —
    the "generation limits"/"concurrent-user protection" requirement.
    Mapped to HTTP 429 at the API layer."""


@dataclass
class AvatarJob:
    id: str
    request: AvatarGenerationRequest
    portrait_path: Path
    face_box: tuple[int, int, int, int]
    job_dir: Path
    status: AvatarJobStatus = "queued"
    progress: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    audio_path: Path | None = None
    video_path: Path | None = None
    duration_s: float | None = None
    engine_name: str | None = None
    processing_time_s: float | None = None
    error_kind: str | None = None
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    # Checked cooperatively between pipeline stages — see module docstring's
    # "Cancellation" section for exactly what this can and can't interrupt.
    cancel_requested: bool = False


class AvatarJobManager:
    def __init__(
        self,
        *,
        pipeline,  # backend.app.services.speech_pipeline.SpeechPipeline — not type-hinted to avoid an import cycle risk, mirrors main.py's own app.state.pipeline duck-typing
        engine: AvatarEngine,
        settings: Settings,
    ) -> None:
        self._pipeline = pipeline
        self._engine = engine
        self._settings = settings
        self._storage_root = Path(settings.avatar_storage_dir)
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._tts_cache_dir = self._storage_root / "_tts_cache"

        self._jobs: dict[str, AvatarJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(settings.avatar_max_concurrent_jobs)
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._worker_tasks: list[asyncio.Task] = []
        self._cleanup_task: asyncio.Task | None = None

    # ---------------------------------------------------------------- lifecycle

    def start(self, *, n_workers: int = 2) -> None:
        self._worker_tasks = [asyncio.create_task(self._worker_loop()) for _ in range(n_workers)]
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        for task in [*self._worker_tasks, self._cleanup_task]:
            if task:
                task.cancel()
        for task in [*self._worker_tasks, self._cleanup_task]:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    # ------------------------------------------------------------------ create

    def create_job(
        self,
        request: AvatarGenerationRequest,
        *,
        portrait: ValidatedPortrait,
        ref_audio_bytes: bytes | None,
    ) -> AvatarJob:
        active = sum(1 for j in self._jobs.values() if j.status not in TERMINAL_STATUSES)
        if active >= self._settings.avatar_max_queued_jobs:
            raise AvatarJobLimitError(
                f"Too many avatar jobs in progress ({active}) — try again in a moment"
            )

        job_id = uuid.uuid4().hex
        job_dir = self._storage_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        # Fixed filename, never derived from user input — no path traversal
        # surface, matches the brief's "no user-controlled filesystem paths".
        portrait_path = job_dir / "portrait.png"
        portrait_path.write_bytes(portrait.normalized_png_bytes)
        if ref_audio_bytes:
            (job_dir / "ref_audio.bin").write_bytes(ref_audio_bytes)

        job = AvatarJob(id=job_id, request=request, portrait_path=portrait_path, face_box=portrait.face_box, job_dir=job_dir)
        self._jobs[job_id] = job
        self._queue.put_nowait(job_id)
        return job

    def get(self, job_id: str) -> AvatarJob | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status in TERMINAL_STATUSES:
            return False
        job.cancel_requested = True
        if job.status == "queued":
            self._transition(job, "cancelled")
        return True

    # --------------------------------------------------------------- subscribe

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """One `asyncio.Queue` per SSE connection — `api/avatar.py`'s events
        endpoint reads from it. Immediately seeded with the job's current
        state so a client connecting mid-job doesn't wait for the *next*
        transition to see where things stand."""
        q: asyncio.Queue = asyncio.Queue()
        job = self._jobs.get(job_id)
        if job is not None:
            q.put_nowait(_snapshot(job))
        self._subscribers.setdefault(job_id, []).append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(job_id)
        if subs and q in subs:
            subs.remove(q)

    def _publish(self, job: AvatarJob) -> None:
        for q in self._subscribers.get(job.id, []):
            q.put_nowait(_snapshot(job))

    # ------------------------------------------------------------------ worker

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if job is None or job.status != "queued":
                continue  # cancelled while still queued, or already handled
            async with self._semaphore:
                await self._run_job(job)

    def _transition(self, job: AvatarJob, status: AvatarJobStatus) -> None:
        job.status = status
        job.progress = job.progress if status in ("failed", "cancelled") else PROGRESS_BY_STATUS[status]
        job.updated_at = time.time()
        self._publish(job)

    def _fail(self, job: AvatarJob, *, kind: str, message: str) -> None:
        job.error_kind = kind
        job.error_message = message
        self._transition(job, "failed")

    async def _run_job(self, job: AvatarJob) -> None:
        t0 = time.perf_counter()
        try:
            if job.cancel_requested:
                self._transition(job, "cancelled")
                return

            self._transition(job, "preprocessing")
            tts_request = _build_tts_request(job.request)

            ref_audio_bytes = None
            ref_audio_file = job.job_dir / "ref_audio.bin"
            if ref_audio_file.exists():
                ref_audio_bytes = ref_audio_file.read_bytes()

            if job.cancel_requested:
                self._transition(job, "cancelled")
                return
            self._transition(job, "generating_audio")
            audio_path = await self._synthesize_audio(job, tts_request, ref_audio_bytes)
            job.audio_path = audio_path

            if job.cancel_requested:
                self._transition(job, "cancelled")
                return
            self._transition(job, "preparing_avatar")
            emotion = EmotionConfig.for_emotion(job.request.emotion)
            options = AvatarOptions(
                fps=self._settings.avatar_fps,
                max_duration_s=self._settings.avatar_max_audio_s,
                work_dir=job.job_dir,
                face_box=job.face_box,
            )

            if job.cancel_requested:
                self._transition(job, "cancelled")
                return
            self._transition(job, "generating_video")
            try:
                result = await asyncio.wait_for(
                    self._engine.generate(
                        image_path=job.portrait_path, audio_path=audio_path, emotion=emotion, options=options
                    ),
                    timeout=self._settings.avatar_job_timeout_s,
                )
            except TimeoutError:
                # See module docstring's "Cancellation" section — the
                # abandoned engine call may still be running; this job is
                # reported failed regardless.
                self._fail(job, kind="timeout", message="Avatar generation timed out")
                return
            except AvatarEngineError as exc:
                self._fail(job, kind=exc.kind, message=exc.message)
                return

            if job.cancel_requested:
                # The engine finished, but a cancellation landed while it
                # was running — discard the result rather than surfacing it.
                try:
                    result.video_path.unlink(missing_ok=True)
                except OSError:
                    pass
                self._transition(job, "cancelled")
                return

            self._transition(job, "encoding")  # see PROGRESS_BY_STATUS's docstring — folded into the engine call above for this engine
            job.video_path = result.video_path
            job.duration_s = result.duration_s
            job.engine_name = self._engine.name
            job.warnings.extend(result.engine_notes)
            job.processing_time_s = time.perf_counter() - t0
            self._transition(job, "completed")

        except (InferenceError, DialectRewriteError) as exc:
            self._fail(job, kind=exc.kind, message=exc.message)
        except Exception:  # noqa: BLE001 - last-resort guard so one bad job can't kill a worker task
            logger.exception("Avatar job %s failed with an unexpected error", job.id)
            self._fail(job, kind="internal_error", message="Avatar generation failed unexpectedly")

    async def _synthesize_audio(self, job: AvatarJob, tts_request: TTSRequest, ref_audio_bytes: bytes | None) -> Path:
        key = tts_cache.cache_key(tts_request, model_repo_id=self._settings.model_repo_id, ref_audio_bytes=ref_audio_bytes)
        cached = tts_cache.get(self._tts_cache_dir, key)
        if cached is not None:
            job.warnings.append("Reused a cached generation for identical text/voice/settings.")
            return cached

        result = await self._pipeline.synthesize(tts_request, ref_audio_bytes=ref_audio_bytes)
        job.warnings.extend(result.warnings)
        from backend.app.services.audio import encode_wav

        wav_bytes = encode_wav(result.samples, result.sample_rate)
        return tts_cache.put(self._tts_cache_dir, key, wav_bytes)

    # ----------------------------------------------------------------- cleanup

    async def _cleanup_loop(self) -> None:
        interval = self._settings.avatar_cleanup_interval_s
        while True:
            await asyncio.sleep(interval)
            try:
                self.cleanup_old_jobs(max_age_s=self._settings.avatar_job_retention_s)
            except Exception:  # noqa: BLE001 - a cleanup bug must never take down the worker loop
                logger.exception("Avatar job cleanup sweep failed")

    def cleanup_old_jobs(self, *, max_age_s: float) -> int:
        """Removes on-disk job directories (portrait/audio/video) whose job
        is terminal and older than `max_age_s`, and drops them from the
        in-memory job table. The TTS cache directory is swept separately —
        it's addressed by content hash, not job id, and deliberately
        outlives any one job. Returns how many job directories were
        removed (surfaced in logs/tests, not the API)."""
        now = time.time()
        removed = 0
        for job_id, job in list(self._jobs.items()):
            if job.status not in TERMINAL_STATUSES:
                continue
            if now - job.updated_at < max_age_s:
                continue
            shutil.rmtree(job.job_dir, ignore_errors=True)
            del self._jobs[job_id]
            self._subscribers.pop(job_id, None)
            removed += 1
        return removed


def _build_tts_request(req: AvatarGenerationRequest) -> TTSRequest:
    DIALECT_BY_ID[req.dialect_id]  # re-validated defensively; AvatarGenerationRequest already checked this
    return TTSRequest(
        text=req.text,
        mode=req.mode,
        pipeline_mode="native",  # avatar audio always goes through the single-call path — see TTSRequest.pipeline_mode's docstring for what dual_model/transliteration are for; neither matters here
        dialect_id=req.dialect_id,
        gender=req.gender,
        pitch=req.pitch,
        ref_text=req.ref_text,
        speed=req.speed,
        quality=req.quality,
        guidance_scale=req.guidance_scale,
    )


def _snapshot(job: AvatarJob):
    from backend.app.models.avatar import AvatarJobEvent

    return AvatarJobEvent(job_id=job.id, status=job.status, progress=job.progress)
