"""Contract tests for POST /api/preprocess and the pipeline_mode-aware
fields on POST /api/tts — against FakeEngine + a pass-through diacritizer
(see conftest.py), never real model weights."""

from __future__ import annotations

from backend.app.services import english_tts
from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def test_preprocess_returns_segments_for_mixed_text():
    client = make_client()
    resp = client.post("/api/preprocess", json={"text": "مرحبا developer اليوم", "dialect_id": "msa"})
    assert resp.status_code == 200
    body = resp.json()
    assert [s["language"] for s in body["segments"]] == ["ar", "en", "ar"]
    assert body["original_text"] == "مرحبا developer اليوم"


def test_preprocess_transliteration_mode_converts_english():
    client = make_client()
    resp = client.post(
        "/api/preprocess",
        json={"text": "hello", "dialect_id": "msa", "pipeline_mode": "transliteration"},
    )
    assert resp.status_code == 200
    seg = resp.json()["segments"][0]
    assert seg["speak_text"] != "hello"


def test_preprocess_rejects_unknown_dialect():
    client = make_client()
    resp = client.post("/api/preprocess", json={"text": "مرحبا", "dialect_id": "atlantis"})
    assert resp.status_code == 422


def test_preprocess_empty_text_returns_no_segments():
    # /api/preprocess is a lightweight preview with no generation cost, so
    # blank input degrades gracefully to an empty preview rather than 4xx —
    # unlike /api/tts, which does reject blank text (see test_api_tts.py).
    client = make_client()
    resp = client.post("/api/preprocess", json={"text": "", "dialect_id": "msa"})
    assert resp.status_code == 200
    assert resp.json()["segments"] == []


def test_tts_response_includes_processed_text_and_segments():
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا بالعالم", "dialect_id": "saudi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipeline_mode"] == "native"
    assert body["processed_text"] == "مرحبا بالعالم"
    assert body["segments"][0]["language"] == "ar"


def test_dual_model_falls_back_to_native_when_english_tts_unavailable(monkeypatch):
    monkeypatch.setattr(english_tts, "_pipeline", None)
    monkeypatch.setattr(english_tts, "_load_error", "espeak-ng not installed (simulated)")
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا meeting اليوم", "dialect_id": "msa", "pipeline_mode": "dual_model"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any("English TTS" in w or "espeak" in w for w in body["warnings"])


def test_dual_model_with_english_tts_available_stitches_segments(monkeypatch):
    import numpy as np

    monkeypatch.setattr(english_tts, "_pipeline", object())  # any non-None sentinel
    monkeypatch.setattr(english_tts, "_load_error", None)
    monkeypatch.setattr(english_tts, "synthesize", lambda text, voice="af_heart": np.zeros(2400, dtype=np.float32))

    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا meeting اليوم", "dialect_id": "msa", "pipeline_mode": "dual_model"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audio_base64"]
    assert not any("English TTS" in w for w in body["warnings"])


def test_dual_model_disabled_for_voice_cloning(monkeypatch):
    import io
    import wave

    import numpy as np

    monkeypatch.setattr(english_tts, "_pipeline", object())
    monkeypatch.setattr(english_tts, "_load_error", None)
    monkeypatch.setattr(english_tts, "synthesize", lambda text, voice="af_heart": np.zeros(2400, dtype=np.float32))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * 2400)
    buf.seek(0)

    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا meeting اليوم", "mode": "clone", "pipeline_mode": "dual_model"},
        files={"ref_audio": ("ref.wav", buf, "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any("voice cloning" in w for w in body["warnings"])
