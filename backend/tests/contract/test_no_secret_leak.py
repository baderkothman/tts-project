"""No internal path, traceback, or secret ever reaches a client response."""

from __future__ import annotations

from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def test_generation_failure_does_not_leak_traceback():
    client = make_client(FakeEngine(fail="generation_failed"))
    resp = client.post("/api/tts", data={"text": "مرحبا"})
    body = resp.text
    assert "Traceback" not in body
    assert "/Users/" not in body
    assert ".py" not in body


def test_invalid_input_error_does_not_leak_internals():
    client = make_client(FakeEngine(fail="invalid_input"))
    resp = client.post("/api/tts", data={"text": "مرحبا"})
    assert "Traceback" not in resp.text
    assert "site-packages" not in resp.text


def test_model_info_never_includes_a_token_field():
    client = make_client()
    resp = client.get("/api/health")
    assert "token" not in resp.text.lower()
    assert "hf_token" not in resp.text.lower()
