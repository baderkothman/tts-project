"""Contract tests for /api/dialect/resolve and /api/dialect/compare (T143, T150)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_resolve_user_selection_wins_ac11():
    resp = client.post("/api/dialect/resolve", json={"text": "شو رأيك", "dialect": "lebanese"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolved_dialect"] == "lebanese"
    assert body["source"] == "user_selected"


def test_resolve_without_selection_degrades_to_200_never_5xx_ac13():
    # No HF_TOKEN configured in the test environment -> classifier
    # unavailable -> must still be 200 with an honest reason, not a 5xx.
    resp = client.post("/api/dialect/resolve", json={"text": "مرحبا"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "classifier"
    assert body["unavailable_reason"] is not None


def test_resolve_empty_text_is_422():
    resp = client.post("/api/dialect/resolve", json={"text": ""})
    assert resp.status_code == 422


def test_compare_returns_two_audio_refs_and_changes_list_ac14():
    resp = client.post(
        "/api/dialect/compare", json={"text": "بكرا عندي meeting عالـ 10", "dialect": "lebanese"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["raw_audio_ref"]
    assert body["corrected_audio_ref"]
    assert isinstance(body["changes"], list)
    assert body["detection"]["resolved_dialect"] == "lebanese"


def test_compare_no_correction_applied_states_it_plainly():
    # Plain text with nothing for any pipeline stage or dictionary entry to
    # change (Story 7, Scenario 3): changes must be empty and both audio
    # renderings must be identical, not fabricated as different.
    resp = client.post("/api/dialect/compare", json={"text": "مرحبا كيف حالك اليوم"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["changes"] == []
    assert body["raw_audio_ref"] == body["corrected_audio_ref"]
