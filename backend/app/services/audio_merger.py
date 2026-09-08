"""Stitch per-segment waveforms (from `arabic_tts`/Lahgtna and
`english_tts`/Kokoro) into one continuous, natural-sounding clip —
used only by the `dual_model` pipeline mode.

Three real seams get smoothed, in order:

1. **Sample rate** — both engines already emit 24kHz (a deliberate reason
   Kokoro was chosen over an otherwise-appealing candidate at a different
   rate), so this is normally a no-op; `librosa.resample` (already a
   transitive dependency via `omnivoice`) runs only when a segment
   genuinely differs, rather than assuming it never will.
2. **Loudness** — each engine has its own default level. `pyloudnorm`
   (ITU-R BS.1770 integrated loudness) normalizes every segment to the same
   target LUFS before concatenation, so switching languages mid-sentence
   doesn't also mean switching volume.
3. **Transitions** — a short linear crossfade plus a small silence pad
   between segments (both configurable) avoids both an audible click at the
   boundary and the "two separate recordings stapled together" effect of a
   hard cut or an unnaturally long pause.
"""

from __future__ import annotations

import numpy as np
import pyloudnorm as pyln

TARGET_SAMPLE_RATE = 24000
TARGET_LUFS = -23.0
DEFAULT_PAUSE_MS = 50.0  # within the spec's 30-80ms guidance for a same-turn language switch
DEFAULT_CROSSFADE_MS = 15.0


def resample_if_needed(samples: np.ndarray, sample_rate: int, target_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    if sample_rate == target_rate or len(samples) == 0:
        return samples
    import librosa

    return librosa.resample(samples.astype(np.float32), orig_sr=sample_rate, target_sr=target_rate)


def normalize_loudness(samples: np.ndarray, sample_rate: int, target_lufs: float = TARGET_LUFS) -> np.ndarray:
    # pyloudnorm's BS.1770 meter needs at least one 0.4s analysis block;
    # anything shorter (a clipped English word, a test fixture) skips
    # normalization rather than raising.
    if len(samples) < sample_rate * 0.4:
        return samples
    meter = pyln.Meter(sample_rate)
    loudness = meter.integrated_loudness(samples.astype(np.float64))
    if loudness == float("-inf"):
        return samples  # effective silence — nothing to normalize
    normalized = pyln.normalize.loudness(samples.astype(np.float64), loudness, target_lufs)
    peak = np.abs(normalized).max()
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)  # guard against clipping after normalization
    return normalized.astype(np.float32)


def _crossfade_concat(a: np.ndarray, b: np.ndarray, sample_rate: int, crossfade_ms: float) -> np.ndarray:
    n = min(int(sample_rate * crossfade_ms / 1000), len(a), len(b))
    if n <= 0:
        return np.concatenate([a, b])
    fade_out = np.linspace(1.0, 0.0, n, dtype=np.float32)
    fade_in = np.linspace(0.0, 1.0, n, dtype=np.float32)
    mixed = a[-n:] * fade_out + b[:n] * fade_in
    return np.concatenate([a[:-n], mixed, b[n:]])


def merge_segments(
    segments: list[tuple[np.ndarray, int]],
    *,
    pause_ms: float = DEFAULT_PAUSE_MS,
    crossfade_ms: float = DEFAULT_CROSSFADE_MS,
    target_lufs: float = TARGET_LUFS,
) -> tuple[np.ndarray, int]:
    """`segments` is a list of (samples, sample_rate) pairs, one per
    language-run, in speaking order. Returns (merged_samples, sample_rate)."""
    if not segments:
        return np.zeros(0, dtype=np.float32), TARGET_SAMPLE_RATE
    if len(segments) == 1:
        samples, rate = segments[0]
        resampled = resample_if_needed(samples, rate)
        return normalize_loudness(resampled, TARGET_SAMPLE_RATE, target_lufs), TARGET_SAMPLE_RATE

    prepared = [
        normalize_loudness(resample_if_needed(samples, rate), TARGET_SAMPLE_RATE, target_lufs)
        for samples, rate in segments
    ]

    pause = np.zeros(int(TARGET_SAMPLE_RATE * pause_ms / 1000), dtype=np.float32)

    merged = prepared[0]
    for next_segment in prepared[1:]:
        merged = _crossfade_concat(merged, pause, TARGET_SAMPLE_RATE, crossfade_ms=0)
        merged = _crossfade_concat(merged, next_segment, TARGET_SAMPLE_RATE, crossfade_ms)

    return merged, TARGET_SAMPLE_RATE
