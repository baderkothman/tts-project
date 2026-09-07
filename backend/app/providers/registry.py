"""Availability-aware provider registry (FR-024, FR-034).

Never raises at import or at registry-build time when credentials are absent
(PC-02) — a provider missing credentials is reported as unavailable and
excluded from automatic routing, not omitted or crashed on (FR-024).
"""

from __future__ import annotations

from backend.app.config import Settings, get_settings
from backend.app.models.voice import ProviderInfo, ProviderStatus
from backend.app.providers.base import TTSProvider
from backend.app.providers.edge import EdgeProvider


def _build_groq(settings: Settings) -> TTSProvider | None:
    try:
        from backend.app.providers.groq import GroqProvider
    except ImportError:
        return None
    return GroqProvider(settings=settings)


def _build_elevenlabs(settings: Settings) -> TTSProvider | None:
    try:
        from backend.app.providers.elevenlabs import ElevenLabsProvider
    except ImportError:
        return None
    return ElevenLabsProvider(settings=settings)


def _build_huggingface(settings: Settings) -> TTSProvider | None:
    try:
        from backend.app.providers.huggingface.provider import HuggingFaceProvider
    except ImportError:
        return None
    return HuggingFaceProvider(settings=settings)


class ProviderRegistry:
    """Holds every configured provider, available or not."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._providers: dict[str, TTSProvider] = {"edge": EdgeProvider()}

        for builder in (_build_groq, _build_elevenlabs, _build_huggingface):
            provider = builder(self._settings)
            if provider is not None:
                self._providers[provider.id] = provider

    @property
    def settings(self) -> Settings:
        return self._settings

    def get(self, provider_id: str) -> TTSProvider | None:
        return self._providers.get(provider_id)

    def all(self) -> list[TTSProvider]:
        return list(self._providers.values())

    def available(self) -> list[TTSProvider]:
        return [p for p in self._providers.values() if p.available() == ProviderStatus.AVAILABLE]

    def default(self) -> TTSProvider | None:
        preferred = self.get(self._settings.tts_default_provider)
        if preferred and preferred.available() == ProviderStatus.AVAILABLE:
            return preferred
        available = self.available()
        return available[0] if available else None

    def fallback(self) -> TTSProvider | None:
        fb = self.get(self._settings.tts_fallback_provider)
        if fb and fb.available() == ProviderStatus.AVAILABLE:
            return fb
        return None

    def info(self) -> list[ProviderInfo]:
        infos = []
        for p in self._providers.values():
            status = p.available()
            infos.append(
                ProviderInfo(
                    id=p.id,
                    display_name=p.display_name,
                    status=status,
                    capabilities=p.capabilities(),
                    voice_count=len(p.capabilities().locales) * 2,
                    unavailable_reason=p.unavailable_reason()
                    if status != ProviderStatus.AVAILABLE
                    else None,
                )
            )
        return infos


_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
