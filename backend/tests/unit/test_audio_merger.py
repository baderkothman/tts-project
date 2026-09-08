from __future__ import annotations

import numpy as np

from backend.app.services import audio_merger


def _tone(duration_s: float, rate: int, amplitude: float = 0.3, freq: float = 220.0) -> np.ndarray:
    t = np.linspace(0, duration_s, int(rate * duration_s), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_resample_is_a_no_op_at_target_rate():
    samples = _tone(0.5, audio_merger.TARGET_SAMPLE_RATE)
    result = audio_merger.resample_if_needed(samples, audio_merger.TARGET_SAMPLE_RATE)
    assert result is samples


def test_resample_changes_length_for_different_rate():
    samples = _tone(0.5, 16000)
    result = audio_merger.resample_if_needed(samples, 16000, target_rate=24000)
    expected_len = int(len(samples) * 24000 / 16000)
    assert abs(len(result) - expected_len) < 5


def test_normalize_loudness_preserves_length():
    samples = _tone(1.0, audio_merger.TARGET_SAMPLE_RATE)
    result = audio_merger.normalize_loudness(samples, audio_merger.TARGET_SAMPLE_RATE)
    assert len(result) == len(samples)


def test_normalize_loudness_never_clips():
    loud = _tone(1.0, audio_merger.TARGET_SAMPLE_RATE, amplitude=0.99)
    result = audio_merger.normalize_loudness(loud, audio_merger.TARGET_SAMPLE_RATE, target_lufs=-10.0)
    assert np.abs(result).max() <= 1.0


def test_normalize_loudness_handles_silence():
    silence = np.zeros(audio_merger.TARGET_SAMPLE_RATE, dtype=np.float32)
    result = audio_merger.normalize_loudness(silence, audio_merger.TARGET_SAMPLE_RATE)
    assert np.allclose(result, 0.0)


def test_merge_single_segment_returns_it_unchanged_in_length():
    samples = _tone(0.5, audio_merger.TARGET_SAMPLE_RATE)
    merged, rate = audio_merger.merge_segments([(samples, audio_merger.TARGET_SAMPLE_RATE)])
    assert rate == audio_merger.TARGET_SAMPLE_RATE
    assert len(merged) == len(samples)


def test_merge_multiple_segments_includes_pause_gap():
    a = _tone(0.5, audio_merger.TARGET_SAMPLE_RATE)
    b = _tone(0.5, audio_merger.TARGET_SAMPLE_RATE)
    merged, rate = audio_merger.merge_segments(
        [(a, audio_merger.TARGET_SAMPLE_RATE), (b, audio_merger.TARGET_SAMPLE_RATE)],
        pause_ms=50,
        crossfade_ms=10,
    )
    # Roughly len(a) + len(b) + pause, give or take the crossfade overlap.
    expected = len(a) + len(b) + int(audio_merger.TARGET_SAMPLE_RATE * 0.05)
    assert abs(len(merged) - expected) < audio_merger.TARGET_SAMPLE_RATE * 0.02


def test_merge_empty_list_returns_silence():
    merged, rate = audio_merger.merge_segments([])
    assert len(merged) == 0
    assert rate == audio_merger.TARGET_SAMPLE_RATE
