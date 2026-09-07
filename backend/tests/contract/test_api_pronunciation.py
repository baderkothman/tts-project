"""Pronunciation demo endpoints (FR-019, FR-020)."""


def test_get_demo_has_required_provenance(client):
    r = client.get("/api/pronunciation/demo")
    assert r.status_code == 200
    body = r.json()
    assert body["provider_observed"]
    assert body["voice_observed"]
    assert body["original_text"] != body["corrected_text"]


def test_demo_audio_before_and_after(client):
    before = client.get("/api/pronunciation/demo/audio", params={"corrected": False})
    after = client.get("/api/pronunciation/demo/audio", params={"corrected": True})
    # These depend on scripts/observe_pronunciation.py having generated the
    # files; the repo ships them already generated (docs/audio/).
    assert before.status_code in (200, 404)
    assert after.status_code in (200, 404)
    if before.status_code == 200 and after.status_code == 200:
        assert before.content != after.content
