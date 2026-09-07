"""Application settings.

Secrets are read from the environment only and are never returned by an API
response or written to a log (Constitution VII, FR-039).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Credentials (optional; absence disables a provider, never crashes) ---
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_model_id: str = "eleven_flash_v2_5"

    # --- Service behaviour ---
    tts_default_provider: str = "edge"
    tts_fallback_provider: str = "edge"
    tts_request_timeout_s: float = 30.0
    tts_max_input_chars: int = 5000

    def has_azure(self) -> bool:
        return bool(self.azure_speech_key and self.azure_speech_region)

    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
