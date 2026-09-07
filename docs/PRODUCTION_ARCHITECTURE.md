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

This prototype requires the dialect to be selected explicitly. Production
would add a lightweight dialect classifier on the incoming STT transcript
(or even on raw audio) to auto-route without asking the user — Egyptian,
Gulf, Levantine, and Maghrebi text have distinguishable lexical markers.

## Pronunciation dictionary storage

Currently a Python list in `dictionary.py` (data, per Constitution III). At
scale this becomes a versioned, queryable store (even a simple JSON/YAML file
per locale, or a small database table) so operators can add rules without a
deploy — the `PronunciationRule` schema is already storage-agnostic.

## Fallback TTS and caching

This prototype's fallback (primary → configured fallback provider) already
demonstrates the pattern (`tts_service.py`); production would add:
- A cache keyed on (processed_text, voice, style) for repeated phrases
  (greetings, common confirmations) — these can skip the network round-trip
  entirely.
- Circuit breakers per provider so a degraded provider is temporarily removed
  from routing rather than retried on every request.

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
