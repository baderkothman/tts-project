"""Provider, voice and locale listing endpoints (FR-023, FR-024)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.data.voices import ALL_LOCALES, LOCALE_DISPLAY
from backend.app.models.voice import ProviderInfo, VoiceConfig
from backend.app.providers.registry import get_registry

router = APIRouter(prefix="/api", tags=["voices"])


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    """Every configured provider, including ones missing credentials — never
    silently omitted (FR-024)."""
    return get_registry().info()


@router.get("/voices", response_model=list[VoiceConfig])
async def list_voices(
    provider: str | None = Query(default=None), locale: str | None = Query(default=None)
) -> list[VoiceConfig]:
    registry = get_registry()
    providers = [registry.get(provider)] if provider else registry.all()
    voices: list[VoiceConfig] = []
    for p in providers:
        if p is None:
            continue
        for v in await p.get_voices():
            if locale and v.locale != locale:
                continue
            voices.append(v)
    return voices


@router.get("/locales")
async def list_locales() -> dict:
    return {
        "locales": ALL_LOCALES,
        "display_names": LOCALE_DISPLAY,
    }
