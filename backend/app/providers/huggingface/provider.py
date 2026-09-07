"""The Hugging Face `TTSProvider` adapter (FR-060).

A fourth adapter, not a parallel system: it implements the exact same
`TTSProvider` interface as Edge/Groq/ElevenLabs and is registered the same
way (`providers/registry.py`). Internally it picks an execution-mode backend
— `inference_api.py` (default, research.md R12), `local.py`, or
`endpoint.py` — per the `HFModelConfig` a voice resolves to; none of the
three backends is itself a `TTSProvider`, which is what keeps
`TTSService`/`VoiceRouter` unaware more than one execution mode exists.

Only the `enabled=True`, `task="dialect_tts"` entries in
`data/hf_model_registry.py` become voices (FR-058) — an unverified or
disabled candidate is never reachable through this adapter.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.config import Settings
from backend.app.data.dialect_profiles import DIALECT_PROFILES
from backend.app.data.hf_model_registry import enabled_for_task
from backend.app.models.dialect import HFModelConfig
from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.providers.huggingface import endpoint, inference_api, local
from backend.app.providers.huggingface.models import HFSynthesisRequest


def _voice_for_model(model: HFModelConfig) -> VoiceConfig:
    # A dialect_tts model may serve more than one DialectProfile; the first
    # match supplies the locale/dialect_family shown in the catalogue.
    profile = next((p for p in DIALECT_PROFILES if model.id in (p.preferred_tts_models or [])), None)
    dialect = profile.dialect_family if profile else None
    locale = profile.locale if profile and profile.locale else "ar"
    return VoiceConfig(
        id=f"huggingface:{model.id}",
        provider="huggingface",
        provider_voice_id=model.repo_id,
        locale=locale,
        dialect=dialect,
        # No speaker/gender metadata is documented on any cleared dialect_tts
        # model card (research.md R11) — labeled honestly rather than
        # inferred (FR-059), unlike Edge/Groq/ElevenLabs voices which do
        # document gender.
        gender="unknown",
        supports_streaming=model.streaming,
        supports_emotions=False,
        supports_ssml=False,
        latency_class=None,
        fallback_voice_id=None,
        display_name=f"{model.repo_id} ({model.task})",
    )


class HuggingFaceProvider(TTSProvider):
    id = "huggingface"
    display_name = "Hugging Face — dialect-specific TTS (experimental)"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def capabilities(self) -> Capabilities:
        voices = self._voices()
        return Capabilities(
            streaming=False,
            ssml=False,
            phoneme=False,
            native_emotions=False,
            prosody_rate=False,
            prosody_pitch=False,
            prosody_volume=False,
            locales=sorted({v.locale for v in voices}),
            formats=[AudioFormat.PCM_24KHZ],
            max_chars=5000,
            requires_credentials=True,
            notes=(
                "Experimental dialect-specific TTS layer (research.md R10-R14). "
                "Only models that cleared the Model Evaluation Matrix's "
                "license/relevance check (FR-058) are exposed as voices; a "
                "listening-verified dialect-accuracy claim, where it exists, is "
                "recorded in docs/DIALECT_EVALUATION.md, not asserted here."
            ),
        )

    def available(self) -> ProviderStatus:
        if self._settings.has_huggingface():
            return ProviderStatus.AVAILABLE
        return ProviderStatus.MISSING_CREDENTIALS

    def unavailable_reason(self) -> str | None:
        if not self._settings.has_huggingface():
            return "Set HF_TOKEN to enable this provider"
        return None

    def _voices(self) -> list[VoiceConfig]:
        return [_voice_for_model(m) for m in enabled_for_task("dialect_tts")]

    async def get_voices(self) -> list[VoiceConfig]:
        return self._voices()

    def _resolve_model(self, voice: VoiceConfig) -> HFModelConfig:
        for model in enabled_for_task("dialect_tts"):
            if model.repo_id == voice.provider_voice_id:
                return model
        raise ProviderError(self.id, "bad_request", f"No enabled Hugging Face model for voice '{voice.id}'")

    async def _synthesize(self, request: ProviderRequest) -> bytes:
        if not self._settings.has_huggingface():
            raise ProviderError(self.id, "auth", "Hugging Face credentials not configured")

        model = self._resolve_model(request.voice)
        hf_request = HFSynthesisRequest(
            text=request.text, model=model, timeout_s=request.timeout_s,
            hf_token=self._settings.hf_token,
        )

        # research.md R12: hosted Inference API first; local only for models
        # explicitly marked local_supported AND when the caller prefers it
        # (not yet exposed as a per-request choice — hosted is the default
        # for every model currently enabled). Dedicated endpoint is
        # documented, not selected by default (never reached here today).
        if model.remote_supported:
            result = await inference_api.synthesize(hf_request)
        elif model.local_supported:
            result = await local.synthesize(hf_request)
        else:
            result = await endpoint.synthesize(hf_request)
        return result.audio_bytes

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        # Not real incremental streaming (capabilities().streaming mirrors
        # each model's own declared streaming flag, currently False for
        # every enabled model) — the complete audio is yielded as one chunk,
        # the same non-streaming-but-stream-compatible pattern groq.py uses.
        yield await self._synthesize(request)

    async def synthesize(self, request: ProviderRequest) -> bytes:
        return await self._synthesize(request)
