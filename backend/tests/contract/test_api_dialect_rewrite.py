"""Contract tests for the automatic AI dialect rewrite step on /api/tts and
/api/preprocess — against `FakeEngine` + a stubbed `dialect_rewriter` (never
a real OpenAI call; see backend/tests/unit/test_dialect_rewriter.py for that
boundary's own tests).

There is no `ai_dialect_rewrite` request field anymore (see
`backend/app/models/tts.py`'s module docstring): the rewrite runs
automatically inside /api/tts whenever `dialect_rewriter.is_configured()` is
true, and it never runs at all for /api/preprocess (the live typing/dialect
preview) — that's the whole point of this file."""

from __future__ import annotations

from backend.app.services import dialect_rewriter, text_preprocessor
from backend.app.services.dialect_rewriter import DialectRewriteError
from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def test_preprocess_never_calls_the_rewriter_even_when_configured(monkeypatch):
    # The live "what will be spoken" preview must never trigger a paid
    # OpenAI call, regardless of server configuration — /api/preprocess
    # fires on every keystroke/dialect change, so calling out here would be
    # real, unnecessary cost. Force "configured" and fail loudly if
    # anything in the preprocess path even builds the client.
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)

    def boom():
        raise AssertionError("no OpenAI client should ever be built by /api/preprocess")

    monkeypatch.setattr(dialect_rewriter, "_client", boom)
    client = make_client()
    resp = client.post("/api/preprocess", json={"text": "مرحبا", "dialect_id": "saudi"})
    assert resp.status_code == 200
    assert resp.json()["processed_text"] == "مرحبا"


def test_tts_skips_rewrite_silently_when_not_configured():
    # No monkeypatching of dialect_rewriter needed: the suite-wide
    # conftest.py fixture already defaults is_configured() to False, so this
    # exercises the real maybe_rewrite() short-circuit end to end.
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "dialect_id": "saudi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed_text"] == "مرحبا"
    assert not any("openai" in w.lower() for w in body["warnings"])


def test_tts_rewrites_automatically_when_configured(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)

    async def fake_rewrite(text, *, dialect_id, gender=None):
        return "هلا فيك"

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "dialect_id": "saudi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed_text"] == "هلا فيك"
    assert any("openai" in w.lower() for w in body["warnings"])


def test_tts_maps_upstream_error_to_502(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)

    async def fake_rewrite(text, *, dialect_id, gender=None):
        raise DialectRewriteError("upstream_error", "AI dialect rewrite failed — try again in a moment")

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)
    client = make_client()
    resp = client.post("/api/tts", data={"text": "مرحبا", "dialect_id": "saudi"})
    assert resp.status_code == 502


def test_empty_preprocessing_falls_back_to_rewritten_text_not_original(monkeypatch):
    # Real reproduced bug: SpeechPipeline._synthesize_single_call's "nothing
    # speakable came out of preprocessing" fallback used to read
    # `request.text` (the original, un-rewritten, un-diacritized input)
    # instead of the AI-rewritten text — so whenever that edge case fired,
    # the model spoke the user's literal MSA input, silently defeating the
    # whole point of the rewrite. Forcing text_preprocessor to return an
    # empty processed_text (regardless of input) isolates exactly that
    # fallback path without needing a real degenerate rewrite.
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)

    async def fake_rewrite(text, *, dialect_id, gender=None):
        return "هلا وربع كيفك اليوم"

    def empty_preprocess(text, *, dialect_id, pipeline_mode):
        return text_preprocessor.PreprocessResult(original_text=text, processed_text="", segments=[])

    # conftest.py's autouse fixture calls preprocess.cache_clear() in its
    # own teardown regardless of what's installed here — keep that working.
    empty_preprocess.cache_clear = lambda: None

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)
    monkeypatch.setattr(text_preprocessor, "preprocess", empty_preprocess)

    engine = FakeEngine()
    client = make_client(engine)
    resp = client.post("/api/tts", data={"text": "مرحبا، كيف حالك اليوم", "dialect_id": "saudi"})
    assert resp.status_code == 200
    # The text actually sent to the TTS engine must be the rewritten
    # dialectal text, never the original request text.
    assert engine.calls[-1].text == "هلا وربع كيفك اليوم"


def test_tts_forwards_voice_gender_to_the_rewriter(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)
    seen = {}

    async def fake_rewrite(text, *, dialect_id, gender=None):
        seen["gender"] = gender
        return text

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)
    client = make_client()
    resp = client.post(
        "/api/tts",
        data={"text": "مرحبا", "dialect_id": "saudi", "mode": "voice_design", "gender": "female"},
    )
    assert resp.status_code == 200
    assert seen["gender"] == "female"


def test_tts_never_forwards_gender_in_clone_mode(monkeypatch):
    import io
    import wave

    monkeypatch.setattr(dialect_rewriter, "is_configured", lambda: True)
    seen = {}

    async def fake_rewrite(text, *, dialect_id, gender=None):
        seen["gender"] = gender
        return text

    monkeypatch.setattr(dialect_rewriter, "rewrite", fake_rewrite)

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
        },
        files={"ref_audio": ("ref.wav", buf, "audio/wav")},
    )
    assert resp.status_code == 200
    assert seen["gender"] is None
