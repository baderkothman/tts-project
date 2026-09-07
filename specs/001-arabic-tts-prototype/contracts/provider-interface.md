# Contract: TTSProvider Interface

**Feature**: `001-arabic-tts-prototype` | **Constitution**: Principle II (Provider Independence)

Every provider adapter implements this interface and nothing outside `backend/app/providers/`
may import a provider SDK or reference a vendor response type.

## Interface

```python
class TTSProvider(ABC):
    id: str
    display_name: str

    @abstractmethod
    async def synthesize(self, request: ProviderRequest) -> bytes:
        """Return complete audio. MUST raise ProviderError on failure."""

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        """Yield audio chunks as they arrive.
        Default implementation raises NotImplementedError; a provider whose
        capabilities.streaming is True MUST override it."""
        raise NotImplementedError

    @abstractmethod
    async def get_voices(self) -> list[VoiceConfig]: ...

    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    def available(self) -> ProviderStatus:
        """Report readiness. MUST NOT raise and MUST NOT perform network I/O."""
```

## Behavioural contract

Every adapter MUST satisfy these, and the conformance suite in
`backend/tests/contract/test_provider_conformance.py` runs them against every registered
provider — including `FakeProvider`, so the suite is meaningful offline.

| ID | Requirement | Verified by |
|----|-------------|-------------|
| PC-01 | `capabilities()` is pure: no I/O, no exception, same result each call | conformance test |
| PC-02 | `available()` returns a status and never raises, even with no credentials | conformance test |
| PC-03 | A provider with `capabilities().streaming is True` overrides `stream()` | conformance test |
| PC-04 | `stream()` yields at least one non-empty chunk for valid input | conformance test |
| PC-05 | Concatenated `stream()` output is valid audio of the declared format | conformance test |
| PC-06 | Every failure surfaces as `ProviderError`, never a vendor-specific exception | conformance test |
| PC-07 | Every network call carries an explicit timeout | code review + timeout test |
| PC-08 | `get_voices()` returns only voices that provider actually serves | conformance test |
| PC-09 | A voice declares `dialect` only where the vendor publishes a locale (FR-027) | catalogue test |
| PC-10 | Credentials never appear in any returned value or raised message | secret-leak test |
| PC-11 | `stream()` stops promptly when the consumer stops iterating (FR: client disconnect) | cancellation test |
| PC-12 | Text is escaped or transported such that markup cannot alter instructions (FR-041) | injection test |

## ProviderError

```python
class ProviderError(Exception):
    provider: str
    kind: Literal[
        "timeout", "auth", "rate_limit", "unavailable", "bad_request", "server",
        "payment_required",
    ]
    retryable: bool
    message: str          # MUST NOT contain credentials or user text
```

`kind` drives fallback policy in `TTSService`: `timeout`, `rate_limit`, `unavailable`, and
`server` trigger a fallback attempt; `auth`, `bad_request`, and `payment_required` do not,
because retrying a malformed, unauthorized, or plan-restricted request on another provider
wastes a call and hides the real fault. `payment_required` (HTTP 402) was added after live
testing found a real, undocumented case: a valid key whose account plan still cannot use a
given voice (ElevenLabs' free tier rejects API calls to public "library" voices) — distinct
from `auth` (the key itself is invalid) and `bad_request` (the request is malformed).

## The Hugging Face provider (FR-060)

`backend/app/providers/huggingface/provider.py` implements this same `TTSProvider`
interface — it is a fourth adapter, not a parallel system. `local.py`/`inference_api.py`/
`endpoint.py` are execution-mode backends `provider.py` chooses between per the
`HFModelConfig` a request resolves to (research.md R11-R12); none of the three backends is
itself a `TTSProvider` — only `provider.py` is, which is what keeps `TTSService` and the
router unaware that more than one execution mode exists underneath.

No new `ProviderError.kind` was needed for this adapter: a local model too large for R10's
hardware ceiling maps to `unavailable` (same as a missing API key); a hosted Inference API
cold start or rate limit maps to `timeout`/`rate_limit` (same fallback-eligible path any
other provider uses); an unverified-license model in the registry (FR-058) is refused at
selection time, before a `ProviderError` would even apply.

The linguistic-processing services (`dialect_classifier.py`, `diacritizer.py`, `g2p.py`,
`pronunciation_model.py`) are explicitly **not** `TTSProvider` implementations — they
produce text/metadata, not audio, and are consumed by `dialect_service.py`, never
registered in `providers/registry.py` (FR-060).

## Adding a provider (SC-010)

Permitted changes: create `backend/app/providers/<name>.py`, add its voices to the
catalogue, register it in `registry.py`. Nothing in `api/`, `services/`, `text_processing/`,
or `models/` may need editing. `backend/tests/contract/test_import_boundaries.py` asserts
this by scanning imports.
