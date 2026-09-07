# Phase 0 Research: Arabic Text-to-Speech Prototype

**Date**: 2026-09-07 | **Feature**: `001-arabic-tts-prototype`

All Technical Context unknowns are resolved below. Evidence is either cited vendor
documentation or a locally executed probe; raw capture is in `docs/PROVIDER_RESEARCH_NOTES.md`.
Per Constitution Principle V (Measured, Not Claimed), each capability claim names its source.

---

## R1. Which providers, and which one is the verified path?

**Decision**: Three adapters — `edge` (Microsoft Edge Neural TTS, credential-free),
`azure` (Azure AI Speech REST, credential-gated), `elevenlabs` (credential-gated).
`edge` is the default and the path verified end-to-end.

**Rationale**: The target environment has no TTS credentials. A prototype whose only paths
require paid keys cannot be executed, benchmarked, or shown to have a *genuinely observed*
pronunciation defect — and FR-019 and Principle V both forbid asserting an unobserved one.
A locally executed probe confirmed `edge` returns 32 Arabic voices across 16 Arabic locales
with real chunked streaming (41 chunks, 29,376 bytes, cold TTFA 2485 ms). That makes the
full pipeline — streaming, routing, benchmarking, pronunciation demo — actually runnable.
Azure and ElevenLabs adapters are implemented to satisfy provider independence and to be
live the moment a key is present.

**Alternatives considered**:
- *Azure or ElevenLabs only*: rejected — unrunnable here, so every acceptance criterion
  would be unverifiable and the pronunciation demo would have to be invented.
- *A local neural model (Coqui/Piper/XTTS)*: rejected — heavy download, weak Arabic
  coverage, no dialect locales, and no bearing on the cloud-provider abstraction the
  feature exists to demonstrate.
- *A recorded-fixture fake only*: rejected as the primary — proves nothing about real
  streaming or latency. Retained instead as a **test** double for the offline suite.

**Honesty constraint carried into docs**: the Edge endpoint is the Microsoft Edge
read-aloud service, not a contractual API. It has no SLA and no published rate limits, and
must be documented as suitable for prototyping while Azure is the production path for the
same voice family.

---

## R2. What Arabic locale and dialect coverage actually exists?

**Decision**: 16 Microsoft Arabic locales, two voices each (one female, one male).
Dialect families map to locales as: **MSA** → ar-SA; **Gulf** → ar-AE, ar-KW, ar-QA, ar-BH,
ar-OM, ar-IQ; **Egyptian** → ar-EG; **Levantine** → ar-LB, ar-SY, ar-JO; **Maghrebi** →
ar-MA, ar-DZ, ar-TN; plus ar-LY, ar-YE.

**Rationale**: Enumerated live from the voice list, and independently matching Microsoft's
published Arabic voice table. Google publishes only `ar-XA` (MSA), so it contributes no
dialect. ElevenLabs publishes no Arabic locale codes at all — its Arabic voices vary by
accent without a documented locale — so per FR-027 the ElevenLabs adapter declares an
**empty dialect set** rather than an inferred one.

**Finding that changes the design**: **No Azure Arabic voice supports speaking styles or
roles.** None are Neural HD or multilingual. Emotional control for Arabic on the Microsoft
voice family therefore cannot use a `style` attribute and must be synthesized from prosody.

**Alternatives considered**: inferring dialect from an ElevenLabs voice's marketing
description — rejected as exactly the unverified claim Principle V prohibits.

---

## R3. How is speaking style expressed when Arabic voices have no style parameter?

**Decision**: A normalized `EmotionStyle` enum in the request model, translated per adapter
through a declared capability. Edge and Azure map style to a **prosody triple**
(rate %, pitch Hz/%, volume %). ElevenLabs maps style to its **voice settings**
(stability / similarity / style exaggeration). Any provider that can express neither
reports the style unsupported in the response rather than ignoring it (FR-028).

**Rationale**: Verified by inspection of the `edge-tts` client signature: `Communicate`
accepts exactly `rate`, `volume`, and `pitch` — no SSML, no style, no phoneme. Azure
supports full SSML `<prosody>` but, per R2, exposes no Arabic style. Prosody mapping is
therefore the only mechanism available, and calling it "emotion" without qualification
would overstate it.

**Documented limitation**: prosody-mapped style is an *approximation* — a warm or excited
reading rendered as rate and pitch shifts, not true affective synthesis. This is stated in
the response as an `approximated` flag and in the documentation, per Principle V.

**Alternatives considered**: silently dropping unsupported styles (rejected — FR-028
forbids it); refusing the request outright (rejected — needlessly fails a usable request
when a reasonable approximation exists).

---

## R4. How should pronunciation be corrected portably?

**Decision**: Provider-independent **orthographic rewriting** is the primary mechanism —
targeted diacritization, phonetic respelling, and alias substitution applied to the text
before synthesis. SSML `<phoneme>` is implemented only as a capability-gated enhancement
for adapters declaring `supports_phoneme`.

**Rationale**: No phoneme mechanism is portable. ElevenLabs restricts `<phoneme>` to
English (IPA/CMU in other languages requires eleven_v3); Google's Chirp 3: HD accepts no
SSML at all; `edge-tts` escapes its input and accepts no markup. Only Azure offers Arabic
`<phoneme>` and custom lexicons. A correction strategy built on phonemes would therefore
work on exactly one of four engines. Rewriting the text works on all of them, because
every engine reads text.

**Design consequence**: `PronunciationRule` carries optional `locale` and `provider` scope
so an Azure-only phoneme rule and a universal respelling rule coexist in one dictionary.

**Alternatives considered**: a full automatic diacritizer (Mishkal / Farasa / CAMeL) —
rejected for now as a heavy dependency whose errors would be *harder* to debug than the
absence of diacritics; targeted rules cover the cases FR-019 actually requires. Recorded as
a future extension point rather than built.

---

## R5. Which audio format, and how does streaming reach the browser?

**Decision**: **MP3, 24 kHz mono, 48 kbit/s** default. FastAPI `StreamingResponse` forwards
each provider chunk as it arrives; the browser plays it with a plain `<audio>` element
pointed at the streaming endpoint.

**Rationale**: MP3 frames are independently decodable, so a browser begins playback on the
first frames without client-side buffering logic — which is what lets the streaming
requirement be *demonstrated* rather than merely claimed. It is also `edge-tts`'s native
output, avoiding a transcode on the measured path. Raw PCM is exposed where supported
because it is what the eventual avatar pipeline will want (no decode latency, trivially
chunkable); Opus is documented for transport efficiency.

**Alternatives considered**: WebSocket + Web Audio API scheduling — rejected as
substantially more client code for no gain at this scope, and it would put audio-assembly
logic in the frontend, violating Principle I. Recorded in the production architecture as
the right choice once barge-in and cancellation are needed.

---

## R6. Where are the latency stage boundaries?

**Decision**: Instrument T0–T7 with `time.perf_counter()`, carried on a `LatencyTrace`
object threaded through the request.

| Mark | Meaning |
|------|---------|
| T0 | Client initiates request (client-supplied, optional) |
| T1 | Server receives request |
| T2 | Text preprocessing complete |
| T3 | Provider request dispatched |
| T4 | First audio byte received from provider |
| T5 | First audio byte written to the client |
| T6 | Client can begin playback (client-reported, optional) |
| T7 | Synthesis complete |

Derived: preprocessing (T2−T1), provider TTFA (T4−T3), backend TTFA (T5−T1), total
generation (T7−T1), audio duration, and real-time factor (generation ÷ audio duration).

**Rationale**: `perf_counter` is monotonic and unaffected by clock adjustment, which
`time.time()` is not. T0 and T6 are client-side and thus optional — reporting them as
server-measured would be false precision.

**Alternatives considered**: OpenTelemetry spans — correct for production and named in the
architecture document, but it would add a dependency and a collector for a single-user
prototype, against Principle VIII.

---

## R7. How are streaming and benchmarking reconciled?

**Decision**: Benchmarks measure the **streaming** path, because TTFA is only meaningful
there. Per provider/voice/sample: one discarded warm-up call, then N measured repetitions.
Aggregate min, max, mean, median, P95 per stage. Persist per-provider JSON plus a
comparison CSV.

**Rationale**: The first call to any provider pays connection setup — the local probe
showed a cold TTFA of 2485 ms, which is connection cost, not synthesis cost. Including it
would misreport steady-state latency; discarding it silently would overstate cold-start
performance. So the warm-up is discarded *and* the fact is recorded in the results file.
P95 uses nearest-rank on small samples, since interpolated percentiles over ~5 points imply
precision that is not there.

**Alternatives considered**: measuring the non-streaming path — rejected, it cannot produce
a TTFA figure at all.

---

## R8. Async client choice

**Decision**: `edge-tts` (which uses `aiohttp` internally) for the Edge adapter; `httpx`
for the Azure and ElevenLabs REST/SSE adapters. Both are async-native.

**Rationale**: `httpx.AsyncClient.stream()` yields `aiter_bytes()`, which maps directly onto
the chunk-forwarding contract, and a single shared client enables connection reuse — the
dominant TTFA cost per R7. Mixing the two clients is acceptable because each is confined to
its adapter and never appears in domain code (Principle II).

**Alternatives considered**: reimplementing the Edge WebSocket protocol with `httpx` to use
one client everywhere — rejected as re-deriving a maintained, working protocol
implementation for cosmetic uniformity.

---

## R9. Testing without credentials

**Decision**: Default `pytest` run is fully offline. A `FakeProvider` yielding fixed bytes
covers routing, fallback, streaming, timeout, and cancellation. Live provider tests are
marked `@pytest.mark.integration` and **skip** when credentials are absent.

**Rationale**: Constitution VIII forbids live paid calls in the default suite; SC-015
requires the suite to pass without credentials, with credential tests skipped rather than
failed. A skipped test reports honestly as "not run"; a failing one would falsely signal a
defect.

**Alternatives considered**: recorded HTTP cassettes (VCR) — deferred; the FakeProvider
gives deterministic control over timeout and mid-stream failure, which replayed cassettes
do not.

---

## Resolved Technical Context

| Unknown | Resolution |
|---------|-----------|
| Language/Version | Python 3.12 |
| Primary dependencies | FastAPI, Uvicorn, Pydantic v2, httpx, edge-tts, pytest, pytest-asyncio |
| Storage | None. Benchmark and demo artifacts are files; no database (Principle VIII) |
| Testing | pytest + pytest-asyncio; offline by default, integration tests credential-gated |
| Target platform | Local machine, Linux/macOS, Python 3.12+ |
| Project type | Web service (Python backend) + static demonstration page |
| Performance goals | Preprocessing P95 < 50 ms @ 500 chars (SC-004); audible before synthesis completes (SC-002) |
| Constraints | No credentials required for the default path; no user text or audio logged or persisted |
| Scale/scope | Single concurrent user; prototype, not a hosted service |
