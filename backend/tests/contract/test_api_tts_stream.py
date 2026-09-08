"""Contract tests for POST /api/tts/stream — the sentence-chunked SSE
variant of /api/tts, against `FakeEngine` (offline). See
`speech_pipeline.SpeechPipeline.synthesize_stream` and
`sentence_splitter.py` for why this exists (real time-to-first-audio
measurement) and why it's scoped to one engine call per sentence."""

from __future__ import annotations

import json

from backend.app.services.fake_engine import FakeEngine
from backend.tests.contract.conftest import make_client


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Turns a raw SSE body into `[(event, payload), ...]` in order."""
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event = "message"
        data_line = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data_line = line[len("data: ") :]
        assert data_line is not None, block
        events.append((event, json.loads(data_line)))
    return events


def test_stream_emits_one_chunk_per_sentence_then_done():
    client = make_client()
    resp = client.post(
        "/api/tts/stream",
        data={"text": "مرحبا بالعالم. كيف حالك اليوم؟", "dialect_id": "msa"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    chunk_events = [p for e, p in events if e == "chunk"]
    done_events = [p for e, p in events if e == "done"]

    assert len(chunk_events) == 2
    assert chunk_events[0]["chunk_index"] == 0
    assert chunk_events[0]["is_final"] is False
    assert chunk_events[1]["chunk_index"] == 1
    assert chunk_events[1]["is_final"] is True
    assert all(c["audio_base64"] for c in chunk_events)

    assert len(done_events) == 1
    done = done_events[0]
    assert done["chunk_count"] == 2
    assert done["ttfa_ms"] is not None
    assert done["ttfa_ms"] <= done["total_ms"]
    assert done["total_audio_duration_ms"] > 0


def test_stream_first_chunk_elapsed_is_the_ttfa_floor():
    client = make_client()
    resp = client.post("/api/tts/stream", data={"text": "جملة واحدة فقط."})
    events = _parse_sse(resp.text)
    chunk = next(p for e, p in events if e == "chunk")
    done = next(p for e, p in events if e == "done")
    assert chunk["elapsed_ms"] == done["ttfa_ms"]


def test_stream_non_native_pipeline_mode_warns_and_still_streams():
    client = make_client()
    resp = client.post(
        "/api/tts/stream",
        data={"text": "hello world", "pipeline_mode": "dual_model"},
    )
    events = _parse_sse(resp.text)
    chunk = next(p for e, p in events if e == "chunk")
    assert any("Streaming always speaks through the Arabic model" in w for w in chunk["warnings"])


def test_stream_empty_text_is_422():
    client = make_client()
    resp = client.post("/api/tts/stream", data={"text": ""})
    assert resp.status_code == 422


def test_stream_engine_not_loaded_emits_error_event():
    client = make_client(FakeEngine(loaded=False))
    resp = client.post("/api/tts/stream", data={"text": "مرحبا"})
    assert resp.status_code == 200  # the SSE stream itself opened fine
    events = _parse_sse(resp.text)
    assert events[0][0] == "error"
    assert events[0][1]["kind"] == "not_loaded"


def test_stream_clone_mode_passes_ref_audio_to_every_chunk():
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * 2400)
    buf.seek(0)

    engine = FakeEngine()
    client = make_client(engine)
    resp = client.post(
        "/api/tts/stream",
        data={"text": "جملة أولى. جملة ثانية.", "mode": "clone"},
        files={"ref_audio": ("ref.wav", buf, "audio/wav")},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert len([p for e, p in events if e == "chunk"]) == 2
    # FakeEngine.generate() doesn't record ref_audio_bytes itself, but it
    # does validate clone mode requires ref_audio — two successful chunk
    # calls with mode="clone" is proof ref_audio_bytes reached every call
    # (the first `_build_request` check already rejects a missing upload
    # before any chunk is generated at all).
    assert len(engine.calls) == 2
    assert all(c.mode == "clone" for c in engine.calls)
