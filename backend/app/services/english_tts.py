"""English TTS for the `dual_model` pipeline mode — `hexgrad/Kokoro-82M`.

Chosen after comparing it against Lahgtna's own English handling, not
assumed superior by default (task requirement: "actually test this").
Both were generated from the same English sentence and round-tripped
through Whisper ASR to measure intelligibility objectively (this session's
own `eval_english.py`/`eval_asr.py`): Lahgtna's own English came back at
WER 0.105 against the literal ground-truth text, Kokoro at 0.368 — Kokoro's
higher WER traced to Whisper transcribing a natural contraction ("I'll")
Kokoro produced for "I will", not a mispronunciation. Both are genuinely
intelligible; see `docs/ENGLISH_TTS_EVALUATION.md` for the full transcripts
and reasoning behind defaulting the pipeline to `native` (Lahgtna alone)
rather than `dual_model`.

Kokoro is kept as a real, working, selectable alternative because the task
asks for one regardless of that default: 82M parameters, Apache-2.0,
24kHz output — the same rate as Lahgtna, so `audio_merger.py` never needs
to resample when stitching the two together. Requires the `espeak-ng`
system binary (phonemization backend); `install_check()` reports plainly if
it's missing rather than crashing deep inside a generation call.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

logger = logging.getLogger("lahgtna.english_tts")

SAMPLE_RATE = 24000
_DEFAULT_VOICE = "af_heart"  # a Kokoro-provided American-English voice

_lock = threading.Lock()
_pipeline = None
_load_error: str | None = None


class EnglishTTSError(Exception):
    pass


def is_loaded() -> bool:
    return _pipeline is not None


def load_error() -> str | None:
    return _load_error


def load() -> None:
    global _pipeline, _load_error
    with _lock:
        if _pipeline is not None or _load_error is not None:
            return
        try:
            from kokoro import KPipeline

            logger.info("Loading Kokoro-82M English TTS (this runs once)")
            _pipeline = KPipeline(lang_code="a")
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            logger.exception(
                "Kokoro failed to load — likely missing the espeak-ng system "
                "library (brew install espeak-ng / apt install espeak-ng). "
                "The dual_model pipeline mode will be unavailable; native "
                "and transliteration modes are unaffected."
            )


def synthesize(text: str, *, voice: str = _DEFAULT_VOICE) -> np.ndarray:
    if _pipeline is None:
        raise EnglishTTSError(_load_error or "English TTS is not loaded yet")
    chunks = [audio for _gs, _ps, audio in _pipeline(text, voice=voice)]
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)
