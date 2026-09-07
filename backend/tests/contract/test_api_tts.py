"""Contract tests for the /api/tts family, against `FakeEngine` (offline)."""

from __future__ import annotations

from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def test_health_reports_loaded():
    client = make_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["device"] == "cpu"


def test_health_reports_not_loaded():
    client = make_client(FakeEngine(loaded=False))
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "loading"


def test_dialects_returns_only_documented_completed_dialects():
    client = make_client()
    resp = client.get("/api/dialects")
    assert resp.status_code == 200
    ids = {d["id"] for d in resp.json()}
    # Every dialect the model card marks "planned" must never appear.
    assert "emirati" not in ids
    assert "kuwaiti" not in ids
    assert "saudi" in ids
    assert "egyptian" in ids


def test_voices_reports_no_fixed_roster():
    client = make_client()
    resp = client.get("/api/voices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["supports_named_voices"] is False
    assert "male" in body["gender_options"]
    assert "female" in body["gender_options"]


def test_empty_text_is_422():
    client = make_client()
    resp = client.post("/api/tts", data={"text": ""})
    assert resp.status_code == 422


def test_unknown_dialect_is_422():
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "dialect_id": "not-a-real-dialect"})
    assert resp.status_code == 422


def test_voice_design_synthesis_succeeds():
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا بالعالم", "dialect_id": "saudi", "gender": "female"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "voice_design"
    assert body["gender"] == "female"
    assert body["sample_rate"] == 24000
    assert body["audio_base64"]
    assert set(body["latency"]) == {"generation_ms", "audio_duration_ms", "real_time_factor"}


def test_written_only_dialect_surfaces_a_warning():
    client = make_client()
    resp = client.post("/api/tts", data={"text": "شلونك", "dialect_id": "yemeni"})
    assert resp.status_code == 200
    assert any("Yemeni" in w for w in resp.json()["warnings"])


def test_clone_mode_without_reference_audio_is_400():
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "mode": "clone"})
    assert resp.status_code == 400


def test_clone_mode_with_reference_audio_succeeds():
    import io
    import wave

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
        data={"text": "مرحبا", "mode": "clone"},
        files={"ref_audio": ("ref.wav", buf, "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "clone"


def test_engine_not_loaded_is_503():
    client = make_client(FakeEngine(loaded=False))
    resp = client.post("/api/tts", data={"text": "مرحبا"})
    assert resp.status_code == 503


def test_generation_failure_is_502():
    client = make_client(FakeEngine(fail="generation_failed"))
    resp = client.post("/api/tts", data={"text": "مرحبا"})
    assert resp.status_code == 502
