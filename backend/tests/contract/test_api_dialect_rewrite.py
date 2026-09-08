"""Contract tests for the `ai_dialect_rewrite` opt-in on /api/preprocess and
/api/tts — against `FakeEngine` + a stubbed `dialect_rewriter.maybe_rewrite`
(never a real OpenAI call; see backend/tests/unit/test_dialect_rewriter.py
for that boundary's own tests)."""

from __future__ import annotations

from backend.app.services import dialect_rewriter, text_preprocessor
from backend.app.services.dialect_rewriter import DialectRewriteError
from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def test_ai_rewrite_off_by_default_builds_no_client(monkeypatch):
    # maybe_rewrite() is always called (it's the single passthrough point),
    # but with ai_dialect_rewrite unset it must short-circuit before ever
    # touching the OpenAI client — real end-to-end path, not a stub.
    def boom():
        raise AssertionError("no OpenAI client should be built when ai_dialect_rewrite is unset")

    monkeypatch.setattr(dialect_rewriter, "_client", boom)
    client = make_client()
    resp = client.post("/api/preprocess", json={"text": "مرحبا", "dialect_id": "saudi"})
    assert resp.status_code == 200
    assert resp.json()["processed_text"] == "مرحبا"


def test_preprocess_applies_rewrite_and_surfaces_warning(monkeypatch):
    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        assert enabled is True
        return "هلا فيك", ["Text rewritten for Saudi (Najdi) via OpenAI (gpt-5-mini) before synthesis."]

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/preprocess",
        json={"text": "مرحبا", "dialect_id": "saudi", "ai_dialect_rewrite": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed_text"] == "هلا فيك"
    assert any("OpenAI" in w for w in body["warnings"])


def test_preprocess_maps_not_configured_to_503(monkeypatch):
    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        raise DialectRewriteError("not_configured", "AI dialect rewrite requires OPENAI_API_KEY")

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/preprocess",
        json={"text": "مرحبا", "dialect_id": "saudi", "ai_dialect_rewrite": True},
    )
    assert resp.status_code == 503
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_tts_maps_upstream_error_to_502(monkeypatch):
    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        raise DialectRewriteError("upstream_error", "AI dialect rewrite failed — try again in a moment")

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا", "dialect_id": "saudi", "ai_dialect_rewrite": "true"},
    )
    assert resp.status_code == 502


def test_tts_uses_rewritten_text_for_synthesis(monkeypatch):
    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        return "هلا فيك", ["rewritten"]

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا", "dialect_id": "saudi", "ai_dialect_rewrite": "true"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed_text"] == "هلا فيك"
    assert "rewritten" in body["warnings"]


def test_empty_preprocessing_falls_back_to_rewritten_text_not_original(monkeypatch):
    # Real reproduced bug: SpeechPipeline._synthesize_single_call's "nothing
    # speakable came out of preprocessing" fallback used to read
    # `request.text` (the original, un-rewritten, un-diacritized input)
    # instead of the AI-rewritten text — so whenever that edge case fired,
    # the model spoke the user's literal MSA input, silently defeating the
    # whole point of turning the toggle on. Forcing text_preprocessor to
    # return an empty processed_text (regardless of input) isolates exactly
    # that fallback path without needing a real degenerate rewrite.
    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        return "هلا وربع كيفك اليوم", ["rewritten"]

    def empty_preprocess(text, *, dialect_id, pipeline_mode):
        return text_preprocessor.PreprocessResult(original_text=text, processed_text="", segments=[])

    # conftest.py's autouse fixture calls preprocess.cache_clear() in its
    # own teardown regardless of what's installed here — keep that working.
    empty_preprocess.cache_clear = lambda: None

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    monkeypatch.setattr(text_preprocessor, "preprocess", empty_preprocess)

    engine = FakeEngine()
    client = make_client(engine)
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا، كيف حالك اليوم", "dialect_id": "saudi", "ai_dialect_rewrite": "true"},
    )
    assert resp.status_code == 200
    # The text actually sent to the TTS engine must be the rewritten
    # dialectal text, never the original request text.
    assert engine.calls[-1].text == "هلا وربع كيفك اليوم"


def test_tts_forwards_voice_gender_to_the_rewriter(monkeypatch):
    seen = {}

    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        seen["gender"] = gender
        return text, []

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={
            "text": "مرحبا",
            "dialect_id": "saudi",
            "mode": "voice_design",
            "gender": "female",
            "ai_dialect_rewrite": "true",
        },
    )
    assert resp.status_code == 200
    assert seen["gender"] == "female"


def test_tts_never_forwards_gender_in_clone_mode(monkeypatch):
    import io
    import wave

    seen = {}

    async def fake_rewrite(text, *, dialect_id, enabled, gender=None):
        seen["gender"] = gender
        return text, []

    monkeypatch.setattr(dialect_rewriter, "maybe_rewrite", fake_rewrite)

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
        data={
            "text": "مرحبا",
            "dialect_id": "saudi",
            "mode": "clone",
            "gender": "female",  # sent anyway (e.g. a stale form field) — must still be ignored
            "ai_dialect_rewrite": "true",
        },
        files={"ref_audio": ("ref.wav", buf, "audio/wav")},
    )
    assert resp.status_code == 200
    assert seen["gender"] is None
