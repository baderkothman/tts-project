"""API contract tests (contracts/http-api.md AC-01, AC-02, AC-10)."""


def test_ac01_empty_text_returns_422(client):
    r = client.post("/api/tts", json={"text": ""})
    assert r.status_code == 422


def test_ac02_over_length_text_returns_422(client):
    r = client.post("/api/tts", json={"text": "أ" * 5001})
    assert r.status_code == 422


def test_ac10_synthesis_response_has_latency(client):
    r = client.post("/api/tts", json={"text": "مرحبا"})
    assert r.status_code == 200
    body = r.json()
    assert "latency" in body
    assert "processed_text" in body
    assert "voice" in body


def test_preview_no_provider_call(client):
    r = client.post("/api/preview", json={"text": "لدي 125 كتاباً"})
    assert r.status_code == 200
    body = r.json()
    assert "مئة وخمسة وعشرون" in body["processed"]


def test_ac08_fallback_reported_through_http_api(client, monkeypatch):
    """A primary failure that resolves via fallback must surface
    used_fallback=true through the actual HTTP response, not just internally."""
    from backend.app.providers.fake import FakeProvider
    from backend.app.providers.registry import ProviderRegistry

    primary = FakeProvider(chunk_count=5, fail_after_chunks=0, fail_kind="timeout")
    primary.id = "primary"
    fallback = FakeProvider(chunk_count=3)
    fallback.id = "fallback"

    registry = ProviderRegistry.__new__(ProviderRegistry)
    registry._settings = type(
        "S",
        (),
        {
            "tts_default_provider": "primary",
            "tts_fallback_provider": "fallback",
            "tts_request_timeout_s": 30.0,
        },
    )()
    registry._providers = {"primary": primary, "fallback": fallback}

    import backend.app.api.tts as tts_module

    monkeypatch.setattr(tts_module, "get_registry", lambda: registry)

    r = client.post("/api/tts", json={"text": "مرحبا", "provider": "primary"})
    assert r.status_code == 200
    body = r.json()
    assert body["used_fallback"] is True
    assert body["provider"] == "fallback"


def test_ac09_no_provider_available_returns_503_service_stays_up(client, monkeypatch):
    """Total provider unavailability is an actionable 503, and the process
    keeps serving other endpoints afterward (FR-034)."""
    from backend.app.providers.registry import ProviderRegistry

    empty_registry = ProviderRegistry.__new__(ProviderRegistry)
    empty_registry._settings = type(
        "S", (), {"tts_default_provider": "nope", "tts_request_timeout_s": 30.0}
    )()
    empty_registry._providers = {}

    import backend.app.api.tts as tts_module

    monkeypatch.setattr(tts_module, "get_registry", lambda: empty_registry)

    r = client.post("/api/tts", json={"text": "مرحبا"})
    assert r.status_code == 503

    # The service itself is still up — a different endpoint still works.
    health = client.get("/health")
    assert health.status_code == 200
