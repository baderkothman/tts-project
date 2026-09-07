"""Preprocessing P95 under 50ms for 500 chars (SC-004)."""

from backend.app.text_processing.pipeline import process_text


def test_preprocessing_p95_under_budget():
    text = ("عندي 125 كتاباً و1,250.50 دولار وتاريخ 27/09/2026 مع API واجتماع meeting. " * 6)[:500]
    import statistics
    from time import perf_counter

    durations = []
    for _ in range(20):
        t0 = perf_counter()
        process_text(text, locale="ar-SA")
        durations.append((perf_counter() - t0) * 1000)

    durations.sort()
    p95 = durations[int(0.95 * len(durations))]
    assert p95 < 50.0, f"P95 preprocessing time {p95:.2f}ms exceeds 50ms budget"
