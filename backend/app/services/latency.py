"""Basic latency measurement — three perf_counter marks (FR-007, research.md R3).

Deliberately simpler than the prior feature's full T0-T7 streaming trace:
spec.md asks for generation time, audio duration, and real-time factor only.
"""

from __future__ import annotations

import io
import wave
from time import perf_counter

from backend.app.models.speech import LatencyInfo


class LatencyTrace:
    def __init__(self) -> None:
        self._t_request_received = perf_counter()
        self._t_provider_call_started: float | None = None
        self._t_audio_received: float | None = None

    def mark_provider_call_started(self) -> None:
        self._t_provider_call_started = perf_counter()

    def mark_audio_received(self) -> None:
        self._t_audio_received = perf_counter()

    def report(self, audio_bytes: bytes) -> LatencyInfo:
        assert self._t_provider_call_started is not None
        assert self._t_audio_received is not None
        generation_ms = (self._t_audio_received - self._t_provider_call_started) * 1000.0
        audio_duration_ms = wav_duration_ms(audio_bytes)
        real_time_factor = generation_ms / audio_duration_ms if audio_duration_ms > 0 else 0.0
        return LatencyInfo(
            generation_ms=generation_ms,
            audio_duration_ms=audio_duration_ms,
            real_time_factor=real_time_factor,
        )


def wav_duration_ms(audio_bytes: bytes) -> float:
    """Duration of a WAV byte string, in milliseconds.

    Live-discovered (T032 quickstart run): Groq's WAV response declares both
    the RIFF and `data` chunk sizes as `0xFFFFFFFF` — an ffmpeg/libavformat
    streaming-header convention (its `Lavf` muxer tag is visible in the
    header) meaning "size unknown at write time," not a real byte count.
    Python's `wave` module trusts that declared size literally, so
    `getnframes()` returns a nonsense multi-hour figure for a one-second
    clip. Fixed by computing frame count from the actual bytes present in
    the `data` subchunk instead of its declared size, falling back to
    `wave`'s own figure only when it looks sane (below the declared-size
    sentinel).
    """
    with wave.open(io.BytesIO(audio_bytes), "rb") as w:
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        rate = w.getframerate()
        declared_frames = w.getnframes()

    if rate == 0:
        return 0.0

    frame_size = channels * sampwidth
    data_index = audio_bytes.find(b"data")
    if data_index != -1 and frame_size > 0:
        actual_data_bytes = len(audio_bytes) - data_index - 8
        actual_frames = actual_data_bytes // frame_size
        # Only trust the declared count when it doesn't exceed what's
        # actually present (a real, bounded WAV) — otherwise use the real
        # byte-derived count.
        frames = declared_frames if declared_frames <= actual_frames else actual_frames
    else:
        frames = declared_frames

    return (frames / rate) * 1000.0
