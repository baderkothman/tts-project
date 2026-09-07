"""Numpy audio <-> WAV bytes, and duration measurement.

The `omnivoice` package returns plain float32 `np.ndarray` waveforms (see
`OmniVoice.generate`'s docstring, confirmed by reading the installed
package) — there is no vendor-specific decoding step here, unlike the prior
Groq adapter which had to work around a malformed streaming WAV header.
`soundfile` writes a correct, fully-specified WAV, so duration is simply
`frames / sample_rate` — no defensive parsing required.
"""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf


def encode_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def duration_ms(samples: np.ndarray, sample_rate: int) -> float:
    if sample_rate <= 0:
        return 0.0
    return (len(samples) / sample_rate) * 1000.0
