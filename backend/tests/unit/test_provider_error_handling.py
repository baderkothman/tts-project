"""FR-008, AC-07, T027: provider failures degrade to a clear 502, never a crash."""

from __future__ import annotations

from backend.app.providers.fake import FakeProvider


def test_provider_error_maps_to_502_with_clear_detail(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.speak._get_provider", lambda: FakeProvider(fail_kind="rate_limit")
    )
    resp = client.post("/api/speak", json={"text": "مرحبا"})
    assert resp.status_code == 502
    assert "rate_limit" in resp.json()["detail"]


def test_timeout_kind_also_maps_to_502(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.speak._get_provider", lambda: FakeProvider(fail_kind="timeout")
    )
    resp = client.post("/api/speak", json={"text": "مرحبا"})
    assert resp.status_code == 502
    assert "timeout" in resp.json()["detail"]
