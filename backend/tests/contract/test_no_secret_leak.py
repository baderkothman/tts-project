"""No credential value in any response, header, or error message (Constitution VII)."""

from __future__ import annotations

from pathlib import Path

from backend.app.providers.groq import GroqProvider


def test_unavailable_reason_never_contains_key_value():
    provider = GroqProvider(api_key="super-secret-value")
    reason = provider.unavailable_reason()
    assert reason is None  # available when a key is present
    provider_no_key = GroqProvider(api_key=None)
    assert "secret" not in (provider_no_key.unavailable_reason() or "").lower()


def test_env_example_has_no_credential_values():
    text = Path(__file__).resolve().parents[3] / ".env.example"
    content = text.read_text()
    for line in content.splitlines():
        if line.strip().startswith("GROQ_API_KEY="):
            assert line.strip() == "GROQ_API_KEY=", "must have no value, names only"
