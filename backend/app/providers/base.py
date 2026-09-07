"""The provider abstraction (FR-010).

Deliberately small for this single-provider phase: `synthesize` and
`list_voices`, per spec.md's own minimal ABC. No `Capabilities` descriptor,
no streaming contract — those existed in the prior feature to support
comparing multiple providers with different capabilities; this feature has
exactly one provider, so that apparatus would be unjustified complexity
(Constitution VIII).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from backend.app.models.voice import Voice

ErrorKind = Literal["timeout", "auth", "rate_limit", "bad_request", "server"]

# Kinds worth reporting as retryable-in-principle (this phase has no
# fallback provider to retry against, but the distinction is still useful
# in the error message and status-code mapping).
RETRYABLE_KINDS: frozenset[str] = frozenset({"timeout", "rate_limit", "server"})


class ProviderError(Exception):
    """The only exception a provider may raise outward.

    ``message`` must never contain a credential (Constitution VII).
    """

    def __init__(self, provider: str, kind: ErrorKind, message: str) -> None:
        self.provider = provider
        self.kind: ErrorKind = kind
        self.message = message
        self.retryable = kind in RETRYABLE_KINDS
        super().__init__(f"[{provider}/{kind}] {message}")


class TTSProvider(ABC):
    """Abstract base every adapter implements."""

    id: str = "base"
    display_name: str = "Base"

    @abstractmethod
    async def synthesize(self, text: str, voice: Voice, *, timeout_s: float) -> bytes:
        """Return complete audio bytes. Raises ProviderError on failure."""

    @abstractmethod
    async def list_voices(self) -> list[Voice]:
        """Voices this provider actually serves."""

    def available(self) -> bool:
        """Whether this provider is usable right now (e.g. credentials
        present). Must not raise and must not perform network I/O."""
        return True

    def unavailable_reason(self) -> str | None:
        return None
