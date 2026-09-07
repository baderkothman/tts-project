"""Application settings.

Env-only, per Constitution VII — no secret is ever hardcoded, returned by a
response, or logged. This feature has exactly one credential (Groq's), unlike
the prior feature's multi-provider settings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    groq_api_key: str | None = None
    request_timeout_s: float = 30.0
    max_input_chars: int = 5000

    def has_groq(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
