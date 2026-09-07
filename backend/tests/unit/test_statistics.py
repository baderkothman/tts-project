"""Statistics computation on known inputs (FR-036, R7)."""

from backend.app.services.benchmark_service import _percentile_95, _stage_stats


def test_stats_on_known_values():
    stats = _stage_stats([10.0, 20.0, 30.0, 40.0, 50.0])
    assert stats.min_ms == 10.0
    assert stats.max_ms == 50.0
    assert stats.mean_ms == 30.0
    assert stats.median_ms == 30.0
    assert stats.count == 5


def test_p95_nearest_rank_small_sample():
    # nearest-rank on 5 values: ceil(0.95*5)-1 = 4 -> the max value
    assert _percentile_95([10.0, 20.0, 30.0, 40.0, 50.0]) == 50.0


def test_p95_empty_list():
    assert _percentile_95([]) == 0.0
