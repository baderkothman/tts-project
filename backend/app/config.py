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
    groq_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_model_id: str = "eleven_flash_v2_5"
    # Hugging Face hosted Inference API token (research.md R12 — optional,
    # same credential-gated-but-not-required pattern as Groq/ElevenLabs).
    hf_token: str | None = None

    # --- Service behaviour ---
    tts_default_provider: str = "edge"
    tts_fallback_provider: str = "edge"
    tts_request_timeout_s: float = 30.0
    tts_max_input_chars: int = 5000

    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key)

    def has_huggingface(self) -> bool:
        return bool(self.hf_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
