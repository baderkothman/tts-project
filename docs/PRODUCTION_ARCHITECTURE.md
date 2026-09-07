# Production Architecture: Toward a Real-Time Arabic Conversational Avatar

This prototype is the first stage of:

```text
Microphone
    ↓
VAD / Turn Detection
    ↓
Streaming Arabic STT
    ↓
LLM
    ↓
Streaming Response Chunker
    ↓
Arabic Preprocessor          ← this prototype
    ↓
Dialect / Voice Router       ← this prototype
    ↓
Streaming Arabic TTS         ← this prototype
    ↓
Avatar / Audio Playback
```

## Where latency accumulates today, and where it will next

Measured in `docs/BENCHMARK_RESULTS.md`: preprocessing is negligible
(<1ms); **provider connection/first-audio cost dominates** (~1.3–2.3s TTFA on
this network path, largely first-connection overhead). In a full avatar
pipeline, five more stages each add their own latency budget:

| Stage | Typical added latency | Mitigation |
|---|---|---|
| VAD / turn detection | 100–300ms (end-of-speech confirmation) | Tune silence threshold aggressively; accept some false triggers |
| Streaming STT | 200–500ms to first partial transcript | Use a streaming-native STT API, not batch |
| LLM first token | 300ms–2s+ depending on model | Use a fast/small model for the first sentence, or start TTS on the first LLM sentence rather than the full response |
| Response chunking | ~0ms if sentence-boundary chunking is cheap | Chunk on punctuation, not fixed token counts |
| TTS connection | This prototype's ~1.3s+ (persistent connection amortizes this after the first turn) | **Keep a warm, persistent connection to the TTS provider across turns** — this is the single highest-leverage fix, since the benchmark shows connection setup, not synthesis, is the dominant cost |

**The single most important architectural change from this prototype to
production**: this prototype opens a new provider connection per request. A
conversational avatar must hold one open (WebSocket) connection per session
and pipe sentence-chunked LLM output through it continuously, which the
benchmark data suggests would eliminate most of the measured TTFA.

## Barge-in and cancellation

The user must be able to interrupt playback. This requires:
- A client-side audio player that can be stopped instantly and cleared.
- A server-side cancellation signal that stops LLM generation and TTS
  synthesis for the interrupted turn (this prototype's streaming endpoint
  already stops consuming the provider when the client disconnects —
  `backend/app/api/tts.py`'s `is_disconnected()` check — the same pattern
  extends to a cancellation token per turn).
- VAD must distinguish "user started talking over the avatar" from
  background noise, which needs energy + a minimum-duration threshold.

## Turn detection and session state

A conversational session needs: current turn owner (user/avatar), partial
transcript buffer, LLM context window, and the dialect/voice/style selected
for that session — held server-side, keyed by a session id, with a TTL.

## Dialect detection

**Updated** (US6-7, FR-048): this is no longer purely a documented future step — a
text-in dialect classifier (`IbrahimAmin/marbertv2-arabic-written-dialect-classifier` via
Hugging Face's hosted Inference API, `text_processing/huggingface/dialect_classifier.py`)
is live behind `POST /api/dialect/resolve`, with user selection always taking precedence
(FR-048) and the classifier's real output reported even when overridden (FR-051). What
remains a *documented, not-built* future step is the **audio-in** variant: for a real
conversational avatar, the classifier would run on the incoming STT transcript (or the raw
audio, via a model like `badrex/mms-300m-arabic-dialect-identifier`, research.md R11 —
rejected for *this* feature only because it's the wrong modality for typed text, not for
audio) rather than on text the user typed.

## Where Hugging Face sits in the full avatar pipeline

```text
Microphone → VAD → Streaming Arabic STT → Dialect Detection (HF, audio-in — not built)
                                                    │
                                                    ▼
                                                   LLM
                                                    │
                                                    ▼
                                      Dialect-Aware Text Processing
                                                    │
                                                    ▼
                              Hugging Face Pronunciation Layer (live today, text-in):
                              dialect_classifier → pronunciation_dictionary
                              → diacritizer/G2P (structurally ready, pending
                              license-confirmed models — docs/HF_MODEL_RESEARCH.md)
                                                    │
                                                    ▼
                                              Voice Router
                                             /            \
                                HF dialect-specific TTS   Existing TTS
                                (eligible, not yet          (Edge/Groq/
                                 listening-confirmed —       ElevenLabs —
                                 egyptian-tts-chatterbox)     always available)
                                             \            /
                                              Streaming TTS
                                                    │
                                                    ▼
                                             Audio / Avatar
```

**The evidence-based recommendation today (FR-062)**: Hugging Face sits as a
**preprocessing layer**, not a synthesis replacement — every live `/api/dialect/compare`
call made during implementation resolved to `architecture_used: "existing_tts"`, because
no HF-native dialect TTS candidate has yet been listening-confirmed (`docs/DIALECT_
EVALUATION.md`). This recommendation is provisional, not final: it reflects what has
actually been measured, and would change the moment a dialect-specific HF TTS model is
confirmed to outperform the existing baseline on the FR-061 rubric.

## Pronunciation dictionary storage

Currently a Python list in `dictionary.py` (data, per Constitution III), extended by a
second, token-level list in `data/pronunciation_dictionary.py` (FR-052, dialect-scoped
names/places/loanwords, distinct from the pattern-matched rules in `dictionary.py`). At
scale both become a versioned, queryable store (even a simple JSON/YAML file per locale, or
a small database table) so operators can add entries without a deploy — both schemas are
already storage-agnostic Pydantic models.

## Hugging Face execution mode at scale

The prototype defaults to the hosted Inference API (research.md R12) specifically because
it needs no warm capacity commitment while candidate models are still being evaluated. At
production scale, once the FR-054 architecture comparison has picked a winning model per
dialect, a **dedicated Inference Endpoint** (`providers/huggingface/endpoint.py`, currently
a documented stub) removes the hosted API's cold-start variance and per-call queueing,
which is the same reasoning already applied in `docs/BENCHMARK_RESULTS.md` to Groq's
observed cold-start and rate-limit behavior. Local MPS/CPU execution remains viable only
for the smallest models (the classifier, diacritizer, G2P) and only where per-request
latency budget tolerates loading a model into a shared process rather than a dedicated
inference server.

## Fallback TTS and caching

This prototype's fallback (primary → configured fallback provider) already
demonstrates the pattern (`tts_service.py`); production would add:
- A cache keyed on (processed_text, voice, style) for repeated phrases
  (greetings, common confirmations) — these can skip the network round-trip
  entirely.
- Circuit breakers per provider so a degraded provider is temporarily removed
  from routing rather than retried on every request.
- **A worked, real example of why this matters**: live-testing this prototype
  against Groq's Orpheus Arabic model found a genuine, vendor-undocumented
  10 requests/minute limit (`docs/BENCHMARK_RESULTS.md`) — a single busy
  conversational session could exhaust it alone. The adapter-level fix here
  (one bounded, `Retry-After`-honoring retry — `groq.py`) is the right amount
  of resilience for a prototype, but is not sufficient at production scale:
  a production deployment needs a **per-provider outbound token bucket**
  sized to the vendor's documented (or, as here, empirically discovered)
  ceiling, so requests queue or shed gracefully *before* hitting 429 at all,
  rather than reacting to it after the fact per-request.

## Observability and distributed tracing

Extend `LatencyTrace` (T0–T7) into OpenTelemetry spans with a correlation ID
per conversational turn, carried through STT → LLM → TTS, so a single slow
turn can be diagnosed stage-by-stage in production — the trace *shape* this
prototype already establishes is what a tracing backend would visualize.

## Security, secrets, authentication, rate limiting

- Secrets: unchanged principle from this prototype — environment/secret
  manager only, never logged (Constitution VII).
- Authentication: a conversational avatar is user-scoped; add session
  authentication (e.g. short-lived JWT) before any WebSocket is accepted.
- **Rate limiting** (FR-042a): not implemented in this prototype — the
  correct production placement is a token-bucket limiter per authenticated
  user/session in front of both the STT and TTS legs, since both are metered,
  paid, external calls. A reverse-proxy-level limiter (e.g. an API gateway)
  is a reasonable first line; per-session in-process limiting is the second.

## Horizontal scaling

The FastAPI service is stateless per request except for the session state
described above; scaling is standard (multiple instances behind a load
balancer), with session affinity or externalized session state (Redis) once
WebSocket sessions are long-lived.

## Privacy

This prototype already does not log or persist user text/audio by default
(FR-040). A production avatar handling live voice conversation must extend
this: no raw audio persistence without explicit consent, redacted transcripts
in traces, and documented retention limits for any session state that is
kept.
