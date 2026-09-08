# Production Architecture — from this prototype to a real-time conversational avatar

This describes the architecture recommended for taking this prototype toward the
stated eventual target: a real-time conversational avatar. Every claim about the
*current* code cites the file it comes from; every recommendation is scoped to a
concrete, checkable reason, not a generic "add Kubernetes and Redis" checklist.

## 1. Where this prototype actually stands today

- **One process, one model instance, one request at a time.** `TTSEngine` (`backend/app/services/inference.py`)
  loads `oddadmix/lahgtna-omnivoice-v2` once at startup and serializes every call behind
  an `asyncio.Lock` — correct for a single-user demo, a hard concurrency ceiling in production
  (request 2 queues behind request 1 even on an idle GPU).
- **No streaming from the model itself.** `OmniVoice.generate()` has no incremental/token-level
  API — it blocks and returns the full `list[np.ndarray]` only when generation is entirely done
  (verified by reading the installed package's public surface: `generate` is the only synthesis
  entry point, return type `list[np.ndarray]`, not a generator). This project's own
  `/api/tts/stream` (`speech_pipeline.SpeechPipeline.synthesize_stream`, `sentence_splitter.py`)
  works around that by calling `generate()` once per sentence and returning each sentence's audio
  as it's ready — real measured numbers in `docs/PERFORMANCE_BENCHMARKS.md`.
- **fp32 inference.** `inference.py`'s `OmniVoice.from_pretrained(..., dtype=torch.float32)` runs
  the full model in 32-bit float. This is a real, unexploited lever: bf16/fp16 typically
  halves compute time on hardware that supports it, at a quality cost that would need to be
  re-measured, not assumed — flagged here as a concrete next experiment, not claimed as a win.
- **Voice cloning re-embeds the reference clip on every call.** `_generate_sync` always passes
  raw `ref_audio`/`ref_text` into `generate()`. The installed package exposes
  `OmniVoice.create_voice_clone_prompt()`, explicitly documented as reusable
  (`generate()`'s own docstring: "`voice_clone_prompt`: Reusable prompt from
  `create_voice_clone_prompt`... overrides `ref_text` and `ref_audio`") — this project never
  calls it. For a fixed avatar persona voice, that's wasted embedding work on every single turn.

## 2. Recommended pipeline for a real-time avatar

```text
User mic ──► Streaming STT ──► LLM (streaming tokens) ──► Sentence buffer ──► TTS worker pool ──► Avatar renderer ──► Speaker/video
                                        │                         │                  │
                                   partial tokens          one sentence at        chunk audio +
                                   as they arrive           a time, as soon        viseme/timing
                                                             as a sentence          data per chunk
                                                             boundary appears
```

The single design idea that matters most: **don't wait for a full LLM response before
starting TTS.** Feed the sentence buffer from the LLM's own token stream, and fire a TTS
call the instant a sentence boundary appears (the same `sentence_splitter.py` boundary
logic already built here) — greeting-length replies then start speaking while the LLM is
still generating the rest, which is where most of a naive pipeline's perceived latency
lives. This is the direct extension of what `/api/tts/stream` already proves on the TTS
side alone; production wires the *LLM's* streaming output into the same sentence-boundary
trigger instead of a pre-written string.

### Latency budget — where time actually goes, and the lever for each stage

| Stage | Typical share of user-perceived delay | Lever |
|---|---|---|
| STT (finalizing the user's utterance) | Endpointing delay — how long silence has to last before STT decides the user stopped | Tune VAD/endpointing aggressiveness; stream partial transcripts to the LLM before finalization when the LLM supports it |
| LLM first token | Model size + prompt length | Smaller/faster model for the interactive path; stream tokens, don't wait for the full completion |
| LLM → first full sentence | However many tokens the model needs to reach `. ! ? ؟ ؛` | Keep system/prompt instructions terse; bias toward shorter first sentences in the persona prompt if the avatar's opening lines allow it |
| TTS first audio | Measured directly in `docs/PERFORMANCE_BENCHMARKS.md` — this project's actual number, not an estimate | Sentence chunking (done); fp16/bf16 (not yet done, see §1); a smaller/distilled TTS model for the interactive tier if quality allows |
| Avatar render (lip-sync) | Depends on the rendering approach (§5) | Amplitude-envelope visemes are near-zero extra latency; forced phoneme alignment adds a measurable per-chunk cost |

## 3. Multi-dialect support in production

This model's dialect handling is a genuine production advantage worth preserving rather
than re-architecting: dialect is a **per-request parameter** (`language`, resolved from
`backend/app/data/dialects.py`), not a separate fine-tuned checkpoint per dialect. One
loaded model instance already serves all 13 dialects + MSA — there is no "swap models for
Egyptian vs. Saudi" cost to design around.

What production should add on top of that:

- **Dialect detection, not just selection.** Today the UI requires the user to pick a
  dialect chip. A conversational avatar should default to detecting the dialect from the
  user's own speech/text and mirroring it — a lightweight text/audio dialect classifier
  in front of the pipeline (small, CPU-viable model; this does **not** need to be Lahgtna
  itself). Only fall back to an explicit picker when detection confidence is low.
- **Per-dialect diacritization correctness stays centralized.** The word-final i'rab
  stripping (`diacritizer.py`, driven by `dialect_id`) already generalizes to all 9
  exposed dialects from one rule, not 9 special cases — keep that property; don't let a
  future "dialect-specific" feature request turn this into 9 forked code paths.
- **Known gaps get removed, not silently shipped.** 4 dialects the model card marked
  "completed" — Palestinian/Lebanese/Syrian (sharing one Levantine code, `apc`, with no
  distinct conditioning) and Yemeni (no language code in the installed package at all) —
  were shipped briefly with an honest warning, then removed outright after user feedback
  that a dialect option producing no real conditioning isn't a working feature just
  because it's disclosed (README's "How dialect and voice actually work"). A production
  dialect-detector inherits the same 9-dialect ceiling, not a workaround for the 4 that
  don't exist here.

## 4. Dynamic voice switching in production

Also already a per-request parameter (`instruct` string, or a cloned reference), not a
fixed roster (`README.md`'s "no invented capabilities" section) — production's job is
mostly about *managing identity consistently*, not adding a capability the model lacks.

- **A voice-profile registry**, not raw params scattered through client code: a small
  table mapping `persona_id -> {instruct_string}` or `persona_id -> {voice_clone_prompt}`.
  For cloned personas, call `create_voice_clone_prompt()` **once** when the persona is
  created/updated and store the resulting prompt — every subsequent turn reuses it instead
  of re-embedding the reference clip on every single sentence, directly fixing the gap
  named in §1.
- **Switching voice mid-conversation** (e.g. the avatar changes persona, or a multi-character
  scene) is then just swapping which stored profile the next `generate()` call references —
  no model reload, since it's the same loaded instance either way.
- **Consistency across sentence chunks matters more here than in the batch case.** Because
  streaming calls `generate()` once per sentence (§1), an inconsistent or partially-applied
  voice profile would be audible as a voice "wobble" between sentences — reusing one stored
  `voice_clone_prompt` per persona (rather than re-deriving it per chunk) is what keeps every
  chunk in a reply sounding like the same speaker.

## 5. Avatar-specific concerns

- **Barge-in / cancellation.** The user interrupts mid-reply. Sentence-level chunking gives
  a cheap, natural cancellation point: stop after the *current* in-flight chunk finishes
  (or drop it if the underlying call supports cancellation) rather than needing to cut
  audio mid-word. The session needs an explicit state machine (`idle -> listening ->
  thinking -> speaking -> (interrupted) -> listening`), with the "speaking" state tracking
  which chunk is in flight so a barge-in event has something concrete to cancel.
- **Lip-sync / visemes.** Two viable tiers, in order of cost:
  1. **Amplitude-envelope-driven mouth movement** — derive open/close intensity directly
     from each chunk's waveform (the same peak data `useWaveformPeaks.ts` already computes
     for the UI's waveform). Cheap, no extra latency, good enough for a stylized avatar.
  2. **Forced phoneme alignment** per chunk (a lightweight aligner run on the chunk's audio
     + its known text) for accurate viseme timing on a realistic avatar. Adds a real
     per-chunk cost — budget and measure it the same way `docs/PERFORMANCE_BENCHMARKS.md`
     measures TTS chunks, don't assume it's free.
  Start with (1); only build (2) if the avatar's visual fidelity actually demands it.
- **Session state**, not just request/response. A conversational avatar is a stateful
  session (conversation history for the LLM, current persona/voice profile, current
  dialect, barge-in state) — the current API is deliberately stateless per-request
  (`POST /api/tts`), which is correct for this prototype's scope but is not the shape
  production needs; production wants a session object a WebSocket/streaming connection is
  bound to for the conversation's lifetime.

## 6. Scaling, caching, observability, security, privacy

- **Scaling.** Horizontal replicas, each owning one warm model instance (the same
  load-once-at-startup pattern `main.py` already uses) — do **not** reach for request
  batching to increase throughput. Batching trades latency for throughput, and latency is
  the whole point of a real-time avatar; prefer more single-request replicas over batching
  within one. Autoscale on GPU queue depth, not just CPU/request-count.
- **Caching.** `text_preprocessor.preprocess()` and `diacritizer._run_model()` already use
  in-process `lru_cache` — real, but per-process and lost on restart or across replicas.
  A shared cache (e.g. Redis, keyed on text+dialect) makes diacritization/preprocessing
  cache hits work across the whole fleet, which matters once there's more than one replica.
  Caching full *audio* output is worth it only for genuinely repeated phrases (a fixed
  greeting, a common confirmation line) — not general conversational replies, which are
  rarely identical twice.
- **Observability.** Correlation ID per conversation turn, spanning STT → LLM → TTS →
  render; log each stage's latency (this prototype already returns `LatencyInfo` per
  request and `ttfa_ms`/`total_ms` per stream — extend that same shape server-side into
  structured logs/metrics, not just the client-facing response). Dashboard p50/p95 TTFA
  specifically, not just mean total latency — the metric that maps to "does this feel
  real-time" is the tail, not the average.
- **Security & rate limiting.** Input length caps already exist
  (`MAX_INPUT_CHARS_HARD_CAP`, `config.py`'s reference-audio size/type limits) — carry
  them forward, add per-session/per-user request-rate quotas at the gateway, and treat
  every user-supplied string (LLM output included, if it's ever interpolated into a prompt
  for another stage) as untrusted input, never re-injected into a system prompt unescaped.
- **Privacy.** Voice-cloning reference audio is biometric-adjacent data. Production should:
  never persist an uploaded reference clip beyond the request unless the user explicitly
  opts into a saved persona with clear consent and a deletion path; if a `voice_clone_prompt`
  is stored (§4), document that it's derived-from-voice data subject to the same deletion
  request; never log raw audio content, only metadata (duration, sample rate, latency).

## 7. Migration path — what changes, what doesn't

| Stays the same | Changes for production |
|---|---|
| One `OmniVoice` instance per process, loaded once at startup (`main.py`'s lifespan pattern) | N replicas of that same pattern behind a load balancer, not one process serving everyone |
| Dialect = a `language` request parameter, not a per-dialect model | Add a detector in front to *choose* that parameter automatically |
| Voice = `instruct` string or cloned reference, not a fixed roster | Add a persona registry that stores precomputed `voice_clone_prompt`s instead of raw reference clips per call |
| Sentence-chunked calls to `generate()` (`sentence_splitter.py`) | Same chunking, but triggered by the LLM's live token stream instead of a complete pre-written string |
| `LatencyInfo` / `ttfa_ms` per request (`models/tts.py`, `/api/tts/stream`) | Same fields, fed into fleet-wide structured logging/metrics instead of only returned to one client |
| fp32 inference | Re-measure at bf16/fp16 before committing to it — a real experiment, not assumed here |
