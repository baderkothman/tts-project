"""Latency instrumentation.

Uses ``perf_counter`` because it is monotonic and unaffected by wall-clock
adjustment, which ``time.time()`` is not (research R6).

Stage marks:
    T0 client request initiated (client-supplied, optional)
    T1 server received request
    T2 preprocessing complete
    T3 provider request dispatched
    T4 first audio byte from provider
    T5 first audio byte written to client
    T6 client can begin playback (client-reported, optional)
    T7 synthesis complete
"""

from __future__ import annotations

from time import perf_counter

from backend.app.models.tts import LatencyReport

# Bytes per second for MP3 at 48 kbit/s — used to estimate audio duration when
# the provider does not report it.
_MP3_48KBPS_BYTES_PER_SEC = 48_000 / 8


class LatencyTrace:
    """Collects stage marks for a single synthesis."""

    def __init__(self, client_t0_ms: float | None = None) -> None:
        self._marks: dict[str, float] = {}
        self.client_t0_ms = client_t0_ms
        self.audio_bytes = 0
        self.mark("T1")

    def mark(self, name: str) -> None:
        """Record a stage boundary. First write wins for first-byte marks."""
        if name not in self._marks:
            self._marks[name] = perf_counter()

    def has(self, name: str) -> bool:
        return name in self._marks

    def _delta_ms(self, start: str, end: str) -> float | None:
        if start not in self._marks or end not in self._marks:
            return None
        return (self._marks[end] - self._marks[start]) * 1000.0

    def audio_duration_ms(self) -> float | None:
        if not self.audio_bytes:
            return None
        return (self.audio_bytes / _MP3_48KBPS_BYTES_PER_SEC) * 1000.0

    def report(self) -> LatencyReport:
        total = self._delta_ms("T1", "T7")
        duration = self.audio_duration_ms()
        rtf: float | None = None
        if total is not None and duration:
            rtf = total / duration

        return LatencyReport(
            preprocessing_ms=self._delta_ms("T1", "T2"),
            provider_ttfa_ms=self._delta_ms("T3", "T4"),
            backend_ttfa_ms=self._delta_ms("T1", "T5"),
            total_generation_ms=total,
            audio_duration_ms=duration,
            real_time_factor=rtf,
            # Only computable when the client supplied its own T0.
            client_ttfa_ms=None,
        )
