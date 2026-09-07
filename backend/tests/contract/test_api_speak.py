"""Contract tests for /api/speak and /api/voices (T020, T025)."""

from __future__ import annotations

from backend.app.providers.fake import FakeProvider


def _use_fake(monkeypatch):
    monkeypatch.setattr("backend.app.api.speak._get_provider", lambda: FakeProvider())


def test_ac01_empty_text_is_422(client):
    resp = client.post("/api/speak", json={"text": ""})
    assert resp.status_code == 422


def test_ac01_whitespace_only_text_is_422(client):
    resp = client.post("/api/speak", json={"text": "   "})
    assert resp.status_code == 422


def test_ac02_unknown_voice_is_400_with_alternatives(client, monkeypatch):
    _use_fake(monkeypatch)
    resp = client.post("/api/speak", json={"text": "مرحبا", "voice_id": "not-a-real-voice"})
    assert resp.status_code == 400
    assert "fake:male-1" in resp.json()["detail"]["valid_alternatives"]


def test_ac03_male_voice_selectable(client, monkeypatch):
    _use_fake(monkeypatch)
    resp = client.post("/api/speak", json={"text": "مرحبا", "gender": "male"})
    assert resp.status_code == 200
    assert resp.json()["voice"]["gender"] == "male"


def test_ac04_female_voice_selectable(client, monkeypatch):
    _use_fake(monkeypatch)
    resp = client.post("/api/speak", json={"text": "مرحبا", "gender": "female"})
    assert resp.status_code == 200
    assert resp.json()["voice"]["gender"] == "female"


def test_ac05_latency_always_present(client, monkeypatch):
    _use_fake(monkeypatch)
    resp = client.post("/api/speak", json={"text": "مرحبا"})
    assert resp.status_code == 200
    latency = resp.json()["latency"]
    assert set(latency) == {"generation_ms", "audio_duration_ms", "real_time_factor"}
    assert all(isinstance(v, (int, float)) for v in latency.values())


def test_get_voices_returns_list(client, monkeypatch):
    _use_fake(monkeypatch)
    resp = client.get("/api/voices")
    assert resp.status_code == 200
    voices = resp.json()
    assert len(voices) == 2
    assert {v["gender"] for v in voices} == {"male", "female"}
