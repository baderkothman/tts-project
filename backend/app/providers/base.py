"""The provider abstraction.

Every vendor integration lives behind this interface. No module outside
``backend/app/providers/`` may import a provider SDK or reference a vendor
response type (Constitution II, SC-010, enforced by
``tests/contract/test_import_boundaries.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel

from backend.app.models.voice import (
    AudioFormat,
    Capabilities,
    EmotionStyle,
    ProviderStatus,
    VoiceConfig,
)

ErrorKind = Literal[
    "timeout", "auth", "rate_limit", "unavailable", "bad_request", "server",
    "payment_required",
]

# Kinds worth retrying on a different provider. `auth`, `bad_request`, and
# `payment_required` are excluded deliberately: retrying a malformed,
# unauthorized, or plan-restricted request elsewhere burns a second call and
# hides the real fault. `payment_required` (HTTP 402) is its own kind rather
# than folded into `bad_request` because it is a distinct, actionable
# condition — the request was well-formed and the key valid, but the account
# plan does not permit it (discovered live: ElevenLabs' free tier rejects
# calls to public "library" voices via the API) — and callers may want to
# handle "fix your plan" differently from "fix your request".
RETRYABLE_KINDS: frozenset[str] = frozenset(
    {"timeout", "rate_limit", "unavailable", "server"}
)


class ProviderError(Exception):
    """The only exception type a provider may raise outward (PC-06).

    ``message`` must never contain credentials or user text (FR-039, FR-040).
    """

    def __init__(self, provider: str, kind: ErrorKind, message: str) -> None:
        self.provider = provider
        self.kind: ErrorKind = kind
        self.message = message
        self.retryable = kind in RETRYABLE_KINDS
        super().__init__(f"[{provider}/{kind}] {message}")


class ProviderRequest(BaseModel):
    """Normalised synthesis request handed to an adapter.

    Carries no vendor-specific field. Each adapter translates it.
    """

    text: str
    voice: VoiceConfig
    emotion: EmotionStyle = EmotionStyle.NEUTRAL
    speaking_rate: float | None = None
    pitch: float | None = None
    output_format: AudioFormat = AudioFormat.MP3_24KHZ
    timeout_s: float = 30.0


class TTSProvider(ABC):
    """Abstract base every adapter implements."""

    id: str = "base"
    display_name: str = "Base"

    @abstractmethod
    async def synthesize(self, request: ProviderRequest) -> bytes:
        """Return complete audio. Raises ProviderError on failure."""

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        """Yield audio chunks as they arrive.

        A provider declaring ``capabilities().streaming`` MUST override this
        (PC-03). The default exists so a non-streaming provider is still a
        valid adapter.
        """
        raise NotImplementedError(f"{self.id} does not support streaming")
        yield b""  # pragma: no cover - makes this an async generator

    @abstractmethod
    async def get_voices(self) -> list[VoiceConfig]:
        """Voices this provider actually serves (PC-08)."""

    @abstractmethod
    def capabilities(self) -> Capabilities:
        """Pure: no I/O, no exception, stable across calls (PC-01)."""

    def available(self) -> ProviderStatus:
        """Readiness. Must not raise and must not do network I/O (PC-02)."""
        return ProviderStatus.AVAILABLE

    def unavailable_reason(self) -> str | None:
        """Human-readable explanation, naming the missing variable (FR-024)."""
        return None
