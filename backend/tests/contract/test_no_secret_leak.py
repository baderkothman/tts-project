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


def test_dialect_rewrite_upstream_failure_does_not_leak_key_or_traceback(monkeypatch):
    from backend.app.services import dialect_rewriter
    from backend.app.services.dialect_rewriter import DialectRewriteError

    # The rewrite is automatic now (no request field) — force "configured"
    # so this failure path actually fires.
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)

    async def fake_rewrite(text, *, dialect_id, gender=None):
        raise DialectRewriteError("upstream_error", "AI dialect rewrite failed — try again in a moment")

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "dialect_id": "saudi"})
    assert "sk-" not in resp.text
    assert "openai_api_key" not in resp.text.lower()
    assert "Traceback" not in resp.text
