"""Unit tests for `ReplicateAvatarEngine` — the real HTTP calls to
Replicate are never made here; `httpx.AsyncClient` is monkeypatched with a
fake client (same "fake the model-shaped external dependency, test the
surrounding logic for real" pattern `test_dialect_rewriter.py` uses for the
OpenAI client). See `docs/AVATAR_SETUP.md` for how this was verified
against the *real* API (a real prediction, a real downloaded MP4) while
building it — this file is the fast, offline regression suite on top of
that one real verification, not a replacement for it."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from backend.app.services.avatar_engine import AvatarEngineError, AvatarOptions, EmotionConfig
from backend.app.services.avatar_engines import replicate_engine


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"", text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content
        self.text = text

    def json(self):
        return self._json


class _FakeAsyncClient:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self._responses.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self._responses.pop(0)


def _install_fake_client(monkeypatch, responses: list[_FakeResponse]) -> _FakeAsyncClient:
    fake = _FakeAsyncClient(responses)
    monkeypatch.setattr(replicate_engine.httpx, "AsyncClient", lambda **kwargs: fake)
    return fake


def _write_wav(path, *, duration_s: float = 2.0, sample_rate: int = 16000) -> None:
    samples = np.zeros(int(sample_rate * duration_s), dtype=np.float32)
    sf.write(str(path), samples, sample_rate)


def _upload_ok(url: str) -> _FakeResponse:
    return _FakeResponse(200, {"urls": {"get": url}})


async def test_generate_succeeds_end_to_end(tmp_path, monkeypatch):
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake-png-bytes")
    audio_path = tmp_path / "audio.wav"
    _write_wav(audio_path, duration_s=2.0)

    responses = [
        _upload_ok("https://api.replicate.com/v1/files/img"),
        _upload_ok("https://api.replicate.com/v1/files/aud"),
        _FakeResponse(200, {"id": "pred-1"}),
        _FakeResponse(200, {"status": "starting"}),
        _FakeResponse(200, {"status": "processing"}),
        _FakeResponse(200, {"status": "succeeded", "output": "https://replicate.delivery/out.mp4"}),
        _FakeResponse(200, content=b"FAKE-MP4-BYTES"),
    ]
    fake = _install_fake_client(monkeypatch, responses)
    monkeypatch.setattr(replicate_engine, "_POLL_INTERVAL_S", 0)

    engine = replicate_engine.ReplicateAvatarEngine("fake-token")
    options = AvatarOptions(work_dir=tmp_path, face_box=(10, 10, 50, 50))
    result = await engine.generate(
        image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("happy"), options=options
    )

    assert result.video_path.read_bytes() == b"FAKE-MP4-BYTES"
    assert result.width == 256 and result.height == 256
    assert result.duration_s == pytest.approx(2.0, abs=0.01)
    assert any("real AI lip sync" in note for note in result.engine_notes)

    # The prediction-creation call carried the mapped emotion params.
    create_call = next(c for c in fake.calls if c[0] == "POST" and c[1].endswith("/predictions"))
    payload = create_call[2]["json"]
    assert payload["input"]["source_image"] == "https://api.replicate.com/v1/files/img"
    assert payload["input"]["driven_audio"] == "https://api.replicate.com/v1/files/aud"
    assert payload["input"]["use_eyeblink"] is True


@pytest.mark.parametrize(
    "emotion_name,expected_scale,expected_still",
    [
        ("neutral", 1.15, True),  # head_motion=0.10 < 0.15
        ("happy", 1.4, False),  # head_motion=0.25
        ("excited", 1.6, False),  # expression_strength=0.60 -> scale capped at the preset's own ceiling
    ],
)
async def test_emotion_maps_to_real_sadtalker_params(tmp_path, monkeypatch, emotion_name, expected_scale, expected_still):
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake")
    audio_path = tmp_path / "audio.wav"
    _write_wav(audio_path, duration_s=1.0)

    responses = [
        _upload_ok("https://api.replicate.com/v1/files/img"),
        _upload_ok("https://api.replicate.com/v1/files/aud"),
        _FakeResponse(200, {"id": "pred-1"}),
        _FakeResponse(200, {"status": "succeeded", "output": "https://replicate.delivery/out.mp4"}),
        _FakeResponse(200, content=b"x"),
    ]
    fake = _install_fake_client(monkeypatch, responses)
    monkeypatch.setattr(replicate_engine, "_POLL_INTERVAL_S", 0)

    engine = replicate_engine.ReplicateAvatarEngine("fake-token")
    options = AvatarOptions(work_dir=tmp_path, face_box=None)
    await engine.generate(
        image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion(emotion_name), options=options
    )

    create_call = next(c for c in fake.calls if c[0] == "POST" and c[1].endswith("/predictions"))
    payload = create_call[2]["json"]["input"]
    assert payload["expression_scale"] == pytest.approx(expected_scale, abs=0.01)
    assert payload["still_mode"] is expected_still


async def test_insufficient_credit_is_not_available(tmp_path, monkeypatch):
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake")
    audio_path = tmp_path / "audio.wav"
    _write_wav(audio_path)

    responses = [
        _upload_ok("https://x/img"),
        _upload_ok("https://x/aud"),
        _FakeResponse(402, text="Insufficient credit"),
    ]
    _install_fake_client(monkeypatch, responses)
    monkeypatch.setattr(replicate_engine, "_POLL_INTERVAL_S", 0)

    engine = replicate_engine.ReplicateAvatarEngine("fake-token")
    options = AvatarOptions(work_dir=tmp_path, face_box=None)
    with pytest.raises(AvatarEngineError) as exc_info:
        await engine.generate(image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("neutral"), options=options)
    assert exc_info.value.kind == "not_available"
    assert "credit" in exc_info.value.message.lower()


async def test_failed_prediction_is_generation_failed(tmp_path, monkeypatch):
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake")
    audio_path = tmp_path / "audio.wav"
    _write_wav(audio_path)

    responses = [
        _upload_ok("https://x/img"),
        _upload_ok("https://x/aud"),
        _FakeResponse(200, {"id": "pred-1"}),
        _FakeResponse(200, {"status": "failed", "error": "some internal model error"}),
    ]
    _install_fake_client(monkeypatch, responses)
    monkeypatch.setattr(replicate_engine, "_POLL_INTERVAL_S", 0)

    engine = replicate_engine.ReplicateAvatarEngine("fake-token")
    options = AvatarOptions(work_dir=tmp_path, face_box=None)
    with pytest.raises(AvatarEngineError) as exc_info:
        await engine.generate(image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("neutral"), options=options)
    assert exc_info.value.kind == "generation_failed"


async def test_polling_times_out_after_max_polls(tmp_path, monkeypatch):
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake")
    audio_path = tmp_path / "audio.wav"
    _write_wav(audio_path)

    monkeypatch.setattr(replicate_engine, "_MAX_POLLS", 3)
    monkeypatch.setattr(replicate_engine, "_POLL_INTERVAL_S", 0)
    responses = [
        _upload_ok("https://x/img"),
        _upload_ok("https://x/aud"),
        _FakeResponse(200, {"id": "pred-1"}),
        _FakeResponse(200, {"status": "processing"}),
        _FakeResponse(200, {"status": "processing"}),
        _FakeResponse(200, {"status": "processing"}),
    ]
    _install_fake_client(monkeypatch, responses)

    engine = replicate_engine.ReplicateAvatarEngine("fake-token")
    options = AvatarOptions(work_dir=tmp_path, face_box=None)
    with pytest.raises(AvatarEngineError) as exc_info:
        await engine.generate(image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("neutral"), options=options)
    assert exc_info.value.kind == "generation_failed"
    assert "timed out" in exc_info.value.message.lower()
