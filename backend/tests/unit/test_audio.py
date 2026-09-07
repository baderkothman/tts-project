from __future__ import annotations

import numpy as np
import soundfile as sf
import io

from backend.app.services.audio import duration_ms, encode_wav


def test_duration_ms_matches_sample_count():
    samples = np.zeros(12000, dtype=np.float32)  # 0.5s at 24kHz
    assert abs(duration_ms(samples, 24000) - 500.0) < 1e-6


def test_duration_ms_handles_zero_rate():
    assert duration_ms(np.zeros(10), 0) == 0.0


def test_encode_wav_round_trips():
    samples = (np.sin(np.linspace(0, 6.28, 24000)) * 0.5).astype(np.float32)
    wav_bytes = encode_wav(samples, 24000)
    decoded, sr = sf.read(io.BytesIO(wav_bytes))
    assert sr == 24000
    assert len(decoded) == len(samples)
