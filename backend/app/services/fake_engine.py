"""Deterministic test double for `TTSEngine` — offline, no model weights.

Mirrors `TTSEngine`'s public surface (`loaded`, `device`, `load_error`,
`sample_rate`, `generate`) so the API layer's tests never need real model
weights or a GPU/MPS device. Not used by `backend/app/main.py`.
"""

from __future__ import annotations

import numpy as np

from backend.app.data.dialects import DIALECT_BY_ID
from backend.app.models.tts import TTSRequest
from backend.app.services.inference import GenerationResult, InferenceError, InferenceErrorKind


class FakeEngine:
    def __init__(self, *, fail: InferenceErrorKind | None = None, loaded: bool = True) -> None:
        self._fail = fail
        self._loaded = loaded
        self.calls: list[TTSRequest] = []

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def device(self) -> str | None:
        return "cpu" if self._loaded else None

    @property
    def load_error(self) -> str | None:
        return None

    @property
    def sample_rate(self) -> int:
        return 24000

    async def generate(self, request: TTSRequest, *, ref_audio_bytes: bytes | None) -> GenerationResult:
        self.calls.append(request)
        if self._fail is not None:
            raise InferenceError(self._fail, f"induced {self._fail} failure")
        if not self._loaded:
            raise InferenceError("not_loaded", "Model is not loaded yet")
        if request.mode == "clone" and not ref_audio_bytes:
            raise InferenceError("invalid_input", "Voice cloning mode requires a reference audio file")

        # No written-only-dialect warning here — that's text_preprocessor's
        # job (see inference.py's TTSEngine for the same note), and every
        # caller in this test suite goes through SpeechPipeline, which
        # always runs preprocessing first.
        DIALECT_BY_ID[request.dialect_id]  # still validate the id like the real engine would

        # 0.5s of silence — enough for duration/latency math to exercise real code.
        samples = np.zeros(12000, dtype=np.float32)
        return GenerationResult(samples=samples, sample_rate=24000, warnings=[])
