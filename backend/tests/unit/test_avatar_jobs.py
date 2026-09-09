"""Unit tests for `AvatarJobManager` — the async job state machine, using
`FakeEngine` (TTS) and `FakeAvatarEngine` (avatar) so nothing here touches
real model weights or a real `ffmpeg` subprocess. See
`backend/tests/integration/test_stub_engine_real_ffmpeg.py` for the
complementary test that *does* exercise `StubAvatarEngine` for real."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.config import Settings
from backend.app.models.avatar import AvatarGenerationRequest, TERMINAL_STATUSES
from backend.app.services import avatar_jobs as avatar_jobs_module
from backend.app.services import diacritizer, text_preprocessor
from backend.app.services.avatar_engines.fake_engine import FakeAvatarEngine
from backend.app.services.avatar_jobs import AvatarJobLimitError, AvatarJobManager
from backend.app.services.dialect_rewriter import DialectRewriteError
from backend.app.services.fake_engine import FakeEngine
from backend.app.services.portrait_validator import ValidatedPortrait
from backend.app.services.speech_pipeline import SpeechPipeline


@pytest.fixture(autouse=True)
def _fake_diacritizer(monkeypatch):
    # Same "obviously-fake, no real weights" convention as
    # test_text_preprocessor.py — without this, SpeechPipeline.synthesize()
    # (via text_preprocessor.preprocess()) loads the real multi-GB
    # Fine-Tashkeel model on the first call any test in this module makes,
    # which is what made the very first test here blow past a 5s timeout.
    monkeypatch.setattr(diacritizer, "diacritize", lambda text, *, dialect_id="msa": (text, False))
    text_preprocessor.preprocess.cache_clear()
    yield
    text_preprocessor.preprocess.cache_clear()


def _settings(tmp_path, **overrides) -> Settings:
    defaults = dict(
        avatar_storage_dir_override=str(tmp_path),
        avatar_job_timeout_s=5.0,
        avatar_max_concurrent_jobs=1,
        avatar_max_queued_jobs=2,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _portrait() -> ValidatedPortrait:
    return ValidatedPortrait(
        width=400, height=400, format="png", face_box=(100, 80, 200, 200), normalized_png_bytes=b"\x89PNG-fake"
    )


def _request(**overrides) -> AvatarGenerationRequest:
    defaults = dict(text="مرحبا", dialect_id="saudi", emotion="happy")
    defaults.update(overrides)
    return AvatarGenerationRequest(**defaults)


async def _wait_for(manager: AvatarJobManager, job_id: str, predicate, *, timeout_s: float = 5.0):
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        job = manager.get(job_id)
        if predicate(job):
            return job
        await asyncio.sleep(0.01)
    raise AssertionError(f"condition not met within {timeout_s}s (last status: {manager.get(job_id).status})")


async def test_job_runs_to_completion(tmp_path):
    manager = AvatarJobManager(pipeline=SpeechPipeline(FakeEngine()), engine=FakeAvatarEngine(), settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        assert job.status == "queued"

        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)
        assert final.status == "completed"
        assert final.progress == 100
        assert final.video_path is not None and final.video_path.exists()
        assert final.audio_path is not None and final.audio_path.exists()
        assert final.engine_name == "fake"
        assert final.processing_time_s is not None
    finally:
        await manager.stop()


async def test_job_limit_is_enforced(tmp_path):
    manager = AvatarJobManager(
        pipeline=SpeechPipeline(FakeEngine()),
        engine=FakeAvatarEngine(delay_s=1.0),  # keep jobs "active" long enough to hit the cap
        settings=_settings(tmp_path, avatar_max_queued_jobs=1),
    )
    manager.start()
    try:
        manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        with pytest.raises(AvatarJobLimitError):
            manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
    finally:
        await manager.stop()


async def test_cancel_a_queued_job_is_immediate(tmp_path):
    # Concurrency capped at 1 and the running slot occupied by a slow job,
    # so the second job created is genuinely still queued when cancelled.
    manager = AvatarJobManager(
        pipeline=SpeechPipeline(FakeEngine()),
        engine=FakeAvatarEngine(delay_s=1.0),
        settings=_settings(tmp_path, avatar_max_concurrent_jobs=1, avatar_max_queued_jobs=5),
    )
    manager.start()
    try:
        blocking = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        await _wait_for(manager, blocking.id, lambda j: j.status != "queued")

        queued = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        assert queued.status == "queued"
        assert manager.cancel(queued.id) is True
        assert manager.get(queued.id).status == "cancelled"
    finally:
        await manager.stop()


async def test_cancel_a_running_job_discards_its_result(tmp_path):
    engine = FakeAvatarEngine(delay_s=0.3)
    manager = AvatarJobManager(pipeline=SpeechPipeline(FakeEngine()), engine=engine, settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        await _wait_for(manager, job.id, lambda j: j.status == "generating_video")

        assert manager.cancel(job.id) is True
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)

        assert final.status == "cancelled"
        assert final.video_path is None
        # The fake engine did produce a file — it must not survive a
        # cancellation that landed while it was running (see
        # avatar_jobs.py's module docstring, "Cancellation").
        assert not (job.job_dir / "output.mp4").exists()
    finally:
        await manager.stop()


async def test_engine_failure_surfaces_as_a_failed_job(tmp_path):
    engine = FakeAvatarEngine(fail="generation_failed")
    manager = AvatarJobManager(pipeline=SpeechPipeline(FakeEngine()), engine=engine, settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)
        assert final.status == "failed"
        assert final.error_kind == "generation_failed"
        assert "induced" in final.error_message
    finally:
        await manager.stop()


async def test_job_times_out_when_the_engine_hangs(tmp_path):
    engine = FakeAvatarEngine(delay_s=1.0)
    manager = AvatarJobManager(
        pipeline=SpeechPipeline(FakeEngine()), engine=engine, settings=_settings(tmp_path, avatar_job_timeout_s=0.05)
    )
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES, timeout_s=3.0)
        assert final.status == "failed"
        assert final.error_kind == "timeout"
    finally:
        await manager.stop()


async def test_tts_engine_failure_surfaces_with_its_own_kind(tmp_path):
    manager = AvatarJobManager(
        pipeline=SpeechPipeline(FakeEngine(fail="not_loaded")), engine=FakeAvatarEngine(), settings=_settings(tmp_path)
    )
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)
        assert final.status == "failed"
        assert final.error_kind == "not_loaded"
    finally:
        await manager.stop()


async def test_ai_dialect_rewrite_processed_text_is_what_gets_spoken(tmp_path, monkeypatch):
    """Mirrors the /api/tts flow: when ai_dialect_rewrite is on, the
    dialect-rewritten/diacritized text — not the raw typed text — is what
    reaches the TTS engine. dialect_rewriter.rewrite() itself is mocked
    (no real OpenAI call, no OPENAI_API_KEY needed); maybe_rewrite() runs
    for real so the "enabled=False is a no-op" contract stays covered too."""

    async def fake_rewrite(text, *, dialect_id, gender=None):
        assert dialect_id == "saudi"
        return "نص معاد صياغته ومُشكَّل"

    monkeypatch.setattr(avatar_jobs_module.dialect_rewriter, "rewrite", fake_rewrite)

    engine = FakeEngine()
    manager = AvatarJobManager(pipeline=SpeechPipeline(engine), engine=FakeAvatarEngine(), settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(ai_dialect_rewrite=True), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)

        assert final.status == "completed"
        assert any("rewritten for" in w.lower() for w in final.warnings)
        assert engine.calls, "TTS engine was never called"
        assert engine.calls[-1].text == "نص معاد صياغته ومُشكَّل"
        # The rewrite already happened once in avatar_jobs.py — SpeechPipeline
        # must not be asked to do it again.
        assert engine.calls[-1].ai_dialect_rewrite is False
    finally:
        await manager.stop()


async def test_ai_dialect_rewrite_off_by_default_leaves_text_untouched(tmp_path):
    engine = FakeEngine()
    manager = AvatarJobManager(pipeline=SpeechPipeline(engine), engine=FakeAvatarEngine(), settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(text="مرحبا"), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)

        assert final.status == "completed"
        assert not any("rewritten for" in w.lower() for w in final.warnings)
        assert engine.calls[-1].text == "مرحبا"
    finally:
        await manager.stop()


async def test_dialect_rewrite_failure_surfaces_as_a_failed_job(tmp_path, monkeypatch):
    async def fake_rewrite(text, *, dialect_id, gender=None):
        raise DialectRewriteError("upstream_error", "induced dialect rewrite failure")

    monkeypatch.setattr(avatar_jobs_module.dialect_rewriter, "rewrite", fake_rewrite)

    manager = AvatarJobManager(pipeline=SpeechPipeline(FakeEngine()), engine=FakeAvatarEngine(), settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(ai_dialect_rewrite=True), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)
        assert final.status == "failed"
        assert final.error_kind == "upstream_error"
    finally:
        await manager.stop()


async def test_cleanup_removes_old_terminal_jobs_but_not_recent_ones(tmp_path):
    manager = AvatarJobManager(pipeline=SpeechPipeline(FakeEngine()), engine=FakeAvatarEngine(), settings=_settings(tmp_path))
    manager.start()
    try:
        job = manager.create_job(_request(), portrait=_portrait(), ref_audio_bytes=None)
        final = await _wait_for(manager, job.id, lambda j: j.status in TERMINAL_STATUSES)
        assert final.job_dir.exists()

        # Not old enough yet.
        removed = manager.cleanup_old_jobs(max_age_s=3600)
        assert removed == 0
        assert manager.get(job.id) is not None
        assert final.job_dir.exists()

        # Backdate it past retention, then sweep for real.
        final.updated_at -= 7200
        removed = manager.cleanup_old_jobs(max_age_s=3600)
        assert removed == 1
        assert manager.get(job.id) is None
        assert not final.job_dir.exists()
    finally:
        await manager.stop()
