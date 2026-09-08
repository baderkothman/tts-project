"""Application settings.

Env-only — no secret or path is ever hardcoded. TTS synthesis itself needs
exactly one model, loaded from Hugging Face Hub
(`oddadmix/lahgtna-omnivoice-v2`), with no provider credential to manage —
unlike the prior Groq-based phase. The one exception is `openai_api_key`
below: an *optional* credential for the opt-in AI dialect rewrite step
(services/dialect_rewriter.py), which never touches audio generation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # The single model this app is allowed to use (task requirement: no
    # other TTS provider, no fallback). Overridable only for pointing at a
    # local snapshot/mirror of the same weights, never a different model.
    model_repo_id: str = "oddadmix/lahgtna-omnivoice-v2"

    # "auto" picks CUDA > MPS > CPU at startup (services/inference.py).
    device: str = "auto"

    # Optional read-scoped HF token — raises the Hub's anonymous rate limit
    # for the one-time model download. Never required, never logged.
    hf_token: str | None = None

    # Where downloaded model weights are cached. `None` (also: an empty
    # string, e.g. an unfilled HF_HOME= line in .env — pydantic-settings
    # treats "set but empty" differently from "unset" for a plain `str`
    # field, so this is coerced explicitly below) resolves to the
    # repo-local .hf_cache/ so a fresh checkout doesn't silently scatter a
    # multi-GB download into ~/.cache or, worse, a relative ./hub next to
    # wherever uvicorn happened to be launched from (a real bug hit once
    # during this project's own development — see git history).
    hf_home: str | None = None

    @field_validator("hf_home", mode="before")
    @classmethod
    def _blank_hf_home_means_unset(cls, v: object) -> object:
        return v or None

    @property
    def resolved_hf_home(self) -> str:
        return self.hf_home or str(_REPO_ROOT / ".hf_cache")

    request_timeout_s: float = 120.0
    max_input_chars: int = 2000

    # Optional AI dialect rewrite step (services/dialect_rewriter.py) — an
    # opt-in, per-request feature, not a core dependency of this app the
    # way the TTS model is. `None` means the feature is simply unavailable
    # (reported honestly via /api/model-info's dialect_rewriter_configured)
    # rather than raising at startup.
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    # 30s, not the more typical-looking 10-15s: measured directly against
    # the real API — gpt-5-mini at "low" reasoning effort (the setting
    # dialect_rewriter.py actually uses, chosen for reliability over the
    # faster-but-flakier "minimal") ran up to ~12s on this task, so 30s
    # leaves real headroom instead of timing out a non-trivial fraction of
    # otherwise-fine requests.
    openai_timeout_s: float = 30.0

    # Reference-audio upload limits (voice cloning mode).
    max_reference_audio_bytes: int = 15 * 1024 * 1024  # 15 MB
    allowed_reference_audio_types: tuple[str, ...] = (
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/ogg",
        "audio/webm",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
