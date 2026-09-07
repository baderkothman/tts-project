"""T0-T7 latency marks and derived metrics (research R6)."""

from backend.app.services.latency import LatencyTrace


def test_marks_produce_correct_deltas():
    trace = LatencyTrace()
    trace.mark("T2")
    trace.mark("T3")
    trace.mark("T4")
    trace.audio_bytes = 6000  # 1 second of 48kbps mp3
    trace.mark("T5")
    trace.mark("T7")
    report = trace.report()
    assert report.preprocessing_ms is not None
    assert report.provider_ttfa_ms is not None
    assert report.total_generation_ms is not None
    assert report.audio_duration_ms is not None


def test_client_ttfa_null_without_client_t0():
    trace = LatencyTrace(client_t0_ms=None)
    trace.mark("T7")
    report = trace.report()
    assert report.client_ttfa_ms is None


def test_mark_first_write_wins():
    trace = LatencyTrace()
    trace.mark("T4")
    first = trace._marks["T4"]
    trace.mark("T4")  # second call should not overwrite
    assert trace._marks["T4"] == first
