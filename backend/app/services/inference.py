"""The one and only speech-synthesis path: `oddadmix/lahgtna-omnivoice-v2`
loaded through the `omnivoice` package's `OmniVoice` class.

Loaded exactly once, at process startup (see `backend/app/main.py`'s
lifespan), and reused for every request — never re-instantiated per call.
Inference is genuinely blocking CPU/GPU work, so every call runs off the
event loop via `asyncio.to_thread`, and calls are serialized with a lock: a
single `torch` module handling two concurrent forward passes on the same
device is not a scenario the underlying framework documents as safe, and
correctness here matters more than the (currently non-existent) benefit of
overlapping two GPU-bound calls on one device.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import soundfile as sf

from backend.app.config import Settings
from backend.app.data.dialects import DIALECT_BY_ID
from backend.app.models.tts import TTSRequest

logger = logging.getLogger("lahgtna.inference")

ArchitectureName = "OmniVoice (Qwen3-0.6B backbone, diffusion audio head)"
BaseModelName = "k2-fsa/OmniVoice"

InferenceErrorKind = Literal["not_loaded", "invalid_input", "generation_failed"]


class InferenceError(Exception):
    def __init__(self, kind: InferenceErrorKind, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


@dataclass
class GenerationResult:
    samples: np.ndarray
    sample_rate: int
    warnings: list[str] = field(default_factory=list)


def resolve_device(preference: str) -> str:
    """cuda > mps > cpu, matching the task's required priority order."""
    import torch

    if preference != "auto":
        return preference
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class TTSEngine:
    """Owns the one `OmniVoice` instance for the process lifetime."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None
        self._device: str | None = None
        self._load_error: str | None = None
        self._lock = asyncio.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def device(self) -> str | None:
        return self._device

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def sample_rate(self) -> int:
        if self._model is None:
            raise InferenceError("not_loaded", "Model is not loaded")
        return int(self._model.sampling_rate)

    def load(self) -> None:
        """Blocking load — call once, off the event loop, at startup."""
        import os

        os.environ.setdefault("HF_HOME", self._settings.resolved_hf_home)
        if self._settings.hf_token:
            os.environ.setdefault("HF_TOKEN", self._settings.hf_token)

        import torch
        from omnivoice import OmniVoice

        device = resolve_device(self._settings.device)
        logger.info(
            "Loading %s on device=%s (this runs once)",
            self._settings.model_repo_id,
            device,
        )
        t0 = time.perf_counter()
        try:
            model = OmniVoice.from_pretrained(
                self._settings.model_repo_id,
                device_map=device,
                dtype=torch.float32,
            )
            model.eval()
        except Exception as exc:  # noqa: BLE001 - surfaced via /api/health, not raised to a client
            self._load_error = str(exc)
            logger.exception("Model load failed")
            raise
        self._model = model
        self._device = device
        logger.info("Model loaded in %.1fs", time.perf_counter() - t0)

    async def generate(
        self,
        request: TTSRequest,
        *,
        ref_audio_bytes: bytes | None,
    ) -> GenerationResult:
        if self._model is None:
            raise InferenceError("not_loaded", "Model is not loaded yet")

        async with self._lock:
            return await asyncio.to_thread(self._generate_sync, request, ref_audio_bytes)

    def _generate_sync(
        self,
        request: TTSRequest,
        ref_audio_bytes: bytes | None,
    ) -> GenerationResult:
        import torch
        from omnivoice import OmniVoiceGenerationConfig

        # The written-only-dialect warning is surfaced once, by
        # text_preprocessor.preprocess() (services/speech_pipeline.py always
        # calls it before reaching here) — not duplicated at this layer.
        warnings: list[str] = []

        dialect = DIALECT_BY_ID[request.dialect_id]
        language = dialect.language_code

        instruct = None
        ref_audio = None
        ref_text = None

        if request.mode == "clone":
            if not ref_audio_bytes:
                raise InferenceError("invalid_input", "Voice cloning mode requires a reference audio file")
            try:
                waveform, sr = sf.read(io.BytesIO(ref_audio_bytes), dtype="float32")
            except Exception as exc:  # noqa: BLE001
                raise InferenceError(
                    "invalid_input", "Reference audio could not be decoded — upload a valid WAV/MP3/FLAC/OGG file"
                ) from exc
            if waveform.ndim > 1:
                waveform = waveform.mean(axis=1)  # downmix to mono
            ref_audio = (torch.from_numpy(waveform), sr)
            ref_text = request.ref_text or None
        elif request.mode == "voice_design":
            parts = []
            if request.gender:
                parts.append(request.gender)
            if request.age:
                parts.append(request.age)
            parts.append(request.pitch)
            if request.whisper:
                parts.append("whisper")
            instruct = ", ".join(parts)
        # mode == "auto": neither instruct nor ref_audio — model picks a voice.

        num_step = 16 if request.quality == "fast" else 32
        gen_config = OmniVoiceGenerationConfig(
            num_step=num_step,
            guidance_scale=request.guidance_scale,
        )

        try:
            audios = self._model.generate(
                text=request.text,
                language=language,
                ref_audio=ref_audio,
                ref_text=ref_text,
                instruct=instruct,
                speed=request.speed,
                generation_config=gen_config,
            )
        except ValueError as exc:
            # The package raises ValueError for a malformed instruct string
            # or similar caller-fixable input problems — surface as 400, not 500.
            raise InferenceError("invalid_input", str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise InferenceError("generation_failed", "Speech generation failed") from exc

        samples = audios[0]
        return GenerationResult(samples=samples, sample_rate=int(self._model.sampling_rate), warnings=warnings)
