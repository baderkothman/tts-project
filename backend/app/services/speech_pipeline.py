"""Top-level orchestrator: text_preprocessor -> (arabic_tts | english_tts) ->
audio_merger, selected by `TTSRequest.pipeline_mode`.

`native` and `transliteration` both resolve to exactly one call into the
existing `TTSEngine` (`inference.py`, playing the "arabic_tts" role from the
task's suggested file layout — kept under its original name rather than
renamed, since it already *is* that module and a rename would touch every
importer for no behavioral reason) with the fully pronunciation-ready text
substituted in; neither needs a second model or audio stitching at all.
Only `dual_model` — and only when the request actually contains an English
segment, Kokoro loaded successfully, and the voice isn't being cloned (a
cloned voice's whole point is one consistent identity; splicing in a
different Kokoro voice for the English words would defeat it, so that
combination deliberately falls back to `native` instead, with a warning) —
takes the per-segment route through `english_tts.py` and `audio_merger.py`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import numpy as np

from backend.app.models.tts import TTSRequest
from backend.app.services import audio_merger, english_tts, text_preprocessor
from backend.app.services.inference import InferenceError, TTSEngine
from backend.app.services.sentence_splitter import split_sentences


@dataclass
class PipelineResult:
    samples: np.ndarray
    sample_rate: int
    warnings: list[str] = field(default_factory=list)
    preview: text_preprocessor.PreprocessResult | None = None


@dataclass
class StreamChunk:
    index: int
    text: str
    samples: np.ndarray
    sample_rate: int
    is_final: bool
    warnings: list[str] = field(default_factory=list)


class SpeechPipeline:
    def __init__(self, arabic_engine: TTSEngine) -> None:
        self._arabic_engine = arabic_engine

    async def synthesize(self, request: TTSRequest, *, ref_audio_bytes: bytes | None) -> PipelineResult:
        preview = text_preprocessor.preprocess(
            request.text, dialect_id=request.dialect_id, pipeline_mode=request.pipeline_mode
        )
        warnings = list(preview.warnings)
        has_english = any(s.language == "en" for s in preview.segments)

        if request.pipeline_mode == "dual_model" and request.mode == "clone" and has_english:
            warnings.append(
                "dual_model isn't used with voice cloning (it would mix in a different English "
                "voice); this request was spoken natively through the cloned voice instead."
            )

        use_dual_model = (
            request.pipeline_mode == "dual_model"
            and has_english
            and request.mode != "clone"
        )

        if use_dual_model and not english_tts.is_loaded():
            warnings.append(
                english_tts.load_error()
                or "English TTS isn't loaded yet — spoke English segments through the Arabic model instead."
            )
            use_dual_model = False

        if use_dual_model:
            result = await self._synthesize_dual_model(request, preview)
        else:
            result = await self._synthesize_single_call(request, preview, ref_audio_bytes)

        result.warnings = warnings + result.warnings
        result.preview = preview
        return result

    async def _synthesize_single_call(
        self, request: TTSRequest, preview: text_preprocessor.PreprocessResult, ref_audio_bytes: bytes | None
    ) -> PipelineResult:
        effective_text = preview.processed_text.strip() or request.text
        modified_request = request.model_copy(update={"text": effective_text})
        gen = await self._arabic_engine.generate(modified_request, ref_audio_bytes=ref_audio_bytes)
        return PipelineResult(samples=gen.samples, sample_rate=gen.sample_rate, warnings=list(gen.warnings))

    async def _synthesize_dual_model(
        self, request: TTSRequest, preview: text_preprocessor.PreprocessResult
    ) -> PipelineResult:
        audio_segments: list[tuple[np.ndarray, int]] = []
        warnings: list[str] = []

        for seg in preview.segments:
            if not seg.speak_text.strip():
                continue
            if seg.language == "ar":
                sub_request = request.model_copy(update={"text": seg.speak_text})
                gen = await self._arabic_engine.generate(sub_request, ref_audio_bytes=None)
                audio_segments.append((gen.samples, gen.sample_rate))
            else:
                try:
                    samples = await asyncio.to_thread(english_tts.synthesize, seg.speak_text)
                    if len(samples):
                        audio_segments.append((samples, english_tts.SAMPLE_RATE))
                except english_tts.EnglishTTSError as exc:
                    warnings.append(f"English segment '{seg.speak_text}' could not be synthesized ({exc}); skipped.")

        if not audio_segments:
            raise InferenceError("generation_failed", "No speakable segments produced any audio")

        merged, rate = audio_merger.merge_segments(audio_segments)
        return PipelineResult(samples=merged, sample_rate=rate, warnings=warnings)

    async def synthesize_stream(
        self, request: TTSRequest, *, ref_audio_bytes: bytes | None
    ) -> AsyncIterator[StreamChunk]:
        """Sentence-chunked streaming: the first chunk's audio is available
        (and yielded) long before the rest of the text has finished
        synthesizing, which is what makes a real "time to first audio"
        measurement possible at all — `synthesize()` above can't produce one
        since nothing is available until the *entire* clip is done (see
        `sentence_splitter.py`'s docstring for why chunking is the only
        lever available with this model).

        Deliberately scoped to one engine: `dual_model`'s per-segment Kokoro
        routing and `clone`'s single-voice-identity requirement don't
        compose cleanly with resplitting the already-processed text into
        sentences, so streaming always speaks through Lahgtna alone — the
        same engine `native` mode uses — regardless of the request's
        `pipeline_mode`. A warning is attached to the first chunk when the
        caller asked for something else, exactly like the existing
        dual_model+clone fallback above.
        """
        preview = text_preprocessor.preprocess(
            request.text, dialect_id=request.dialect_id, pipeline_mode=request.pipeline_mode
        )
        text = preview.processed_text.strip() or request.text
        chunks = split_sentences(text)
        if not chunks:
            raise InferenceError("invalid_input", "No speakable text after preprocessing")

        warnings = list(preview.warnings)
        if request.pipeline_mode != "native":
            warnings.append(
                "Streaming always speaks through the Arabic model alone (like native mode); "
                f"'{request.pipeline_mode}' English handling isn't available while streaming."
            )

        last_index = len(chunks) - 1
        for i, chunk_text in enumerate(chunks):
            sub_request = request.model_copy(update={"text": chunk_text})
            # ref_audio_bytes goes on every chunk, not just the first: each
            # `generate()` call is independent (no cached voice-clone
            # embedding reuse in inference.py), so a cloned voice's identity
            # would drift or reset on chunk 2+ without it. Harmless for
            # non-clone modes — `_generate_sync` only reads it when
            # `mode == "clone"`.
            gen = await self._arabic_engine.generate(sub_request, ref_audio_bytes=ref_audio_bytes)
            yield StreamChunk(
                index=i,
                text=chunk_text,
                samples=gen.samples,
                sample_rate=gen.sample_rate,
                is_final=(i == last_index),
                warnings=(warnings + gen.warnings) if i == 0 else list(gen.warnings),
            )
