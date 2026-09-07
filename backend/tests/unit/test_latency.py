"""T023."""

from __future__ import annotations

import io
import wave

from backend.app.services.latency import LatencyTrace, wav_duration_ms


def _make_wav(seconds: float, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    n_frames = int(seconds * rate)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


def test_wav_duration_from_frame_count():
    audio = _make_wav(0.5)
    assert abs(wav_duration_ms(audio) - 500.0) < 1.0


def test_wav_duration_handles_ffmpeg_streaming_sentinel_header():
    """Regression: live-discovered (T032) that Groq's real WAV response
    declares both the RIFF and `data` chunk sizes as 0xFFFFFFFF (an
    ffmpeg/libavformat streaming-header convention), which the raw `wave`
    module would otherwise misread as an hours-long clip."""
    real = _make_wav(1.0)
    # Rewrite the RIFF size (offset 4) and data-chunk size (right after the
    # literal b"data") to the 0xFFFFFFFF sentinel, exactly as Groq's
    # response does, keeping the actual audio bytes unchanged.
    data_index = real.find(b"data")
    corrupted = (
        real[:4] + b"\xff\xff\xff\xff" + real[8:data_index + 4]
        + b"\xff\xff\xff\xff" + real[data_index + 8:]
    )
    assert abs(wav_duration_ms(corrupted) - 1000.0) < 1.0


def test_latency_trace_reports_all_fields():
    trace = LatencyTrace()
    trace.mark_provider_call_started()
    trace.mark_audio_received()
    info = trace.report(_make_wav(1.0))
    assert info.generation_ms >= 0
    assert abs(info.audio_duration_ms - 1000.0) < 1.0
    assert info.real_time_factor >= 0
