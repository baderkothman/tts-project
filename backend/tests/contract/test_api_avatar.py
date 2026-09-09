"""Contract tests for POST /api/tts/avatar and the job endpoints around it.
`FakeEngine` (TTS) + `FakeAvatarEngine` (avatar) throughout — no real
model, no real ffmpeg — matching `test_api_tts.py`'s own convention for the
existing endpoint."""

from __future__ import annotations

import io
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.api import avatar as avatar_module
from backend.app.config import Settings
from backend.app.services import avatar_jobs as avatar_jobs_module
from backend.app.services import diacritizer, portrait_validator, text_preprocessor
from backend.app.services.avatar_engines.fake_engine import FakeAvatarEngine
from backend.app.services.avatar_jobs import AvatarJobManager
from backend.app.services.fake_engine import FakeEngine
from backend.app.services.speech_pipeline import SpeechPipeline


@pytest.fixture(autouse=True)
def _fake_diacritizer(monkeypatch):
    # Same convention as backend/tests/contract/conftest.py's fixture for
    # /api/tts's own tests — this file has its own FastAPI app (built by
    # make_client() below, not the one in conftest.py), so it needs its own
    # copy of the same fixture rather than inheriting one that's wired to a
    # different app.
    monkeypatch.setattr(diacritizer, "diacritize", lambda text, *, dialect_id="msa": (text, False))
    text_preprocessor.preprocess.cache_clear()
    yield
    text_preprocessor.preprocess.cache_clear()


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), (180, 140, 110)).save(buf, format="PNG")
    return buf.getvalue()


def make_client(tmp_path, *, avatar_engine=None, tts_engine=None, **settings_overrides) -> TestClient:
    settings = Settings(avatar_storage_dir_override=str(tmp_path), **settings_overrides)
    manager = AvatarJobManager(
        pipeline=SpeechPipeline(tts_engine or FakeEngine()), engine=avatar_engine or FakeAvatarEngine(), settings=settings
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.start()
        try:
            yield
        finally:
            await manager.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(avatar_module.router)
    app.state.avatar_jobs = manager
    return TestClient(app)


def _create_job(client: TestClient, **form_overrides) -> dict:
    form = {"text": "مرحبا", "dialect_id": "saudi", "emotion": "happy"}
    form.update(form_overrides)
    response = client.post("/api/tts/avatar", data=form, files={"portrait": ("portrait.png", _png_bytes(), "image/png")})
    return response


def test_create_job_returns_202_with_job_id(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(tmp_path) as client:
        response = _create_job(client)
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["job_id"]


def test_job_reaches_completed_and_exposes_media_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(tmp_path) as client:
        job_id = _create_job(client).json()["job_id"]

        final = None
        for _ in range(200):
            body = client.get(f"/api/tts/avatar/jobs/{job_id}").json()
            if body["status"] in ("completed", "failed", "cancelled"):
                final = body
                break
        assert final is not None, "job never reached a terminal status"
        assert final["status"] == "completed"
        assert final["progress"] == 100
        assert final["video_url"] == f"/api/tts/avatar/jobs/{job_id}/video"
        assert final["audio_url"] == f"/api/tts/avatar/jobs/{job_id}/audio"
        assert final["engine"] == "fake"

        video_response = client.get(final["video_url"])
        assert video_response.status_code == 200
        assert video_response.content == b"FAKE-MP4-CONTENT"

        audio_response = client.get(final["audio_url"])
        assert audio_response.status_code == 200


def test_unknown_job_id_returns_404(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/api/tts/avatar/jobs/does-not-exist").status_code == 404
        assert client.post("/api/tts/avatar/jobs/does-not-exist/cancel").status_code == 404
        assert client.get("/api/tts/avatar/jobs/does-not-exist/video").status_code == 404


def test_no_face_in_portrait_is_a_400(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [])
    with make_client(tmp_path) as client:
        response = _create_job(client)
        assert response.status_code == 400
        assert "face" in response.json()["detail"].lower()


def test_unsupported_portrait_format_is_a_415(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/tts/avatar",
            data={"text": "مرحبا", "dialect_id": "saudi"},
            files={"portrait": ("portrait.gif", b"not-a-real-gif", "image/gif")},
        )
        assert response.status_code == 415


def test_blank_text_is_a_422(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(tmp_path) as client:
        assert _create_job(client, text="   ").status_code == 422


def test_job_limit_returns_429(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(tmp_path, avatar_engine=FakeAvatarEngine(delay_s=1.0), avatar_max_queued_jobs=1) as client:
        assert _create_job(client).status_code == 202
        assert _create_job(client).status_code == 429


def test_cancel_a_queued_job(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(
        tmp_path, avatar_engine=FakeAvatarEngine(delay_s=1.0), avatar_max_concurrent_jobs=1, avatar_max_queued_jobs=5
    ) as client:
        _create_job(client)  # occupies the one concurrency slot
        second_id = _create_job(client).json()["job_id"]

        cancel_response = client.post(f"/api/tts/avatar/jobs/{second_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["cancelled"] is True

        body = client.get(f"/api/tts/avatar/jobs/{second_id}").json()
        assert body["status"] == "cancelled"


def test_ai_dialect_rewrite_form_field_reaches_the_tts_engine(tmp_path, monkeypatch):
    """End-to-end through the real HTTP form: the ai_dialect_rewrite=true
    field actually changes what text the TTS engine receives, same
    contract as /api/tts's own toggle — no real OpenAI call (rewrite() is
    mocked), just proving the plumbing."""
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])

    async def fake_rewrite(text, *, dialect_id, gender=None):
        return "نص بديل"

    monkeypatch.setattr(avatar_jobs_module.dialect_rewriter, "rewrite", fake_rewrite)

    tts_engine = FakeEngine()
    with make_client(tmp_path, tts_engine=tts_engine) as client:
        job_id = _create_job(client, ai_dialect_rewrite="true").json()["job_id"]

        final = None
        for _ in range(200):
            body = client.get(f"/api/tts/avatar/jobs/{job_id}").json()
            if body["status"] in ("completed", "failed", "cancelled"):
                final = body
                break
        assert final is not None and final["status"] == "completed"
        assert any("rewritten for" in w.lower() for w in final["warnings"])
        assert tts_engine.calls[-1].text == "نص بديل"


def test_emotions_endpoint_lists_the_closed_vocabulary(tmp_path):
    with make_client(tmp_path) as client:
        body = client.get("/api/tts/avatar/emotions").json()
        assert set(body["emotions"]) == {"neutral", "happy", "sad", "excited", "calm", "professional"}
        assert body["default"] == "neutral"


def test_job_events_stream_reaches_a_terminal_status(tmp_path, monkeypatch):
    monkeypatch.setattr(portrait_validator, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    with make_client(tmp_path) as client:
        job_id = _create_job(client).json()["job_id"]
        statuses = []
        with client.stream("GET", f"/api/tts/avatar/jobs/{job_id}/events") as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                import json

                event = json.loads(line[len("data: ") :])
                statuses.append(event["status"])
                if event["status"] in ("completed", "failed", "cancelled"):
                    break
        # `subscribe()` always seeds the stream with the job's *current*
        # status first — with fake engines this fast, the job can genuinely
        # already be "completed" by the time this test's HTTP client
        # connects, so asserting on statuses[0] being some particular
        # in-progress value would be asserting a race, not a real contract.
        # What the contract does guarantee: at least one event, and the
        # stream ends exactly on a terminal status.
        assert statuses
        assert statuses[-1] == "completed"
