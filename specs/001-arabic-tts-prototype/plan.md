# Implementation Plan: Arabic Text-to-Speech Prototype

**Branch**: `001-arabic-tts-prototype` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-arabic-tts-prototype/spec.md`

## Summary

Build a Python-first Arabic TTS service in which Arabic text passes through a pure-function
preprocessing pipeline (normalization → numbers → dates → currencies → abbreviations →
code-switching → pronunciation rules → provider formatting), is routed by dialect and voice
to one of three interchangeable provider adapters behind a single abstract interface, and is
streamed back chunk-by-chunk so playback starts before synthesis finishes. Every stage
boundary is timed with a monotonic clock so time-to-first-audio is measured rather than
estimated, and a benchmark harness replays a fixed Arabic sample set to produce distribution
statistics persisted as files.

The technical approach is set by one finding from Phase 0: **no Arabic pronunciation or
emotion control is portable across providers** — Azure has SSML phonemes but no Arabic
speaking styles, ElevenLabs restricts phonemes to English, Google's Chirp 3 accepts no
markup, and the Edge client escapes all input. Correction is therefore implemented as
provider-independent orthographic rewriting in Python, with markup-based control as a
capability-gated enhancement. This is what keeps the pipeline the asset rather than any
vendor integration.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic v2, httpx (async, for Azure/ElevenLabs
REST and SSE), edge-tts (Microsoft Edge Neural TTS client), pytest, pytest-asyncio

**Storage**: None. No database. Benchmark results and demonstration audio are written as
files under `benchmarks/` and `docs/`; user text and audio are never persisted.

**Testing**: pytest + pytest-asyncio. Default run is fully offline against a `FakeProvider`;
live provider tests carry `@pytest.mark.integration` and skip when credentials are absent.

**Target Platform**: Local machine (macOS/Linux), Python 3.12+, modern browser for the demo page

**Project Type**: Web service (Python backend) with a static, build-free demonstration page

**Performance Goals**: Preprocessing P95 under 50 ms for 500 characters (SC-004); first audio
audible before synthesis completes for passages ≥200 characters in ≥9 of 10 attempts (SC-002);
real-time factor reported per synthesis so avatar feasibility can be judged

**Constraints**: The default path must work with **no credentials** (Assumptions, R1); no user
text or generated audio logged or persisted; every provider call carries an explicit timeout;
markup injection prevented by construction, not by filtering

**Scale/Scope**: Single concurrent user; prototype demonstrating a pipeline, not a hosted
multi-tenant service. Roughly 25 Python modules plus tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Gate | Initial | Post-Design |
|---|-----------|------|---------|-------------|
| I | Python-First Backend | All preprocessing, routing, benchmarking and metrics live in Python; frontend holds no domain logic | PASS | PASS — frontend is one static page that only posts requests, plays an `<audio>` src, and renders returned fields |
| II | Provider Independence | No provider SDK imported outside `providers/`; no domain branch on provider name | PASS | PASS — verified by design: `TTSProvider` ABC + `Capabilities` descriptor; router consults capability data, never a vendor name. Enforced by an automated import test (T082) |
| III | Arabic Linguistic Correctness | Hamza/taa-marbuta/alif-maqsura never folded; existing diacritics preserved; rules are data | PASS | PASS — `normalizer.py` explicitly excludes meaning-changing folds and documents why; `PronunciationRule` records are data loaded from a dictionary module |
| IV | Latency Is A Feature | Async throughout, streaming-first, TTFA instrumented | PASS | PASS — `async def` end to end; `StreamingResponse` forwards each chunk; `LatencyTrace` marks T0–T7 |
| V | Measured, Not Claimed | Every capability claim cited or executed; pronunciation defect actually observed | PASS | PASS — Phase 0 cites each claim; T076 **observes** the defect by synthesis before T077 documents it. The demo cannot be written before the observation step runs |
| VI | Graceful Degradation | Explicit timeouts, configured fallback, missing credentials → unavailable not crash | PASS | PASS — `TTSService` catches `ProviderError`/timeout and retries the fallback; `available()` is checked at registry build, never at import |
| VII | Secure By Default | Env-only secrets, no text/audio logging, length limits, injection prevented by construction | PASS | PASS — `config.py` reads env only; SSML built by an escaping builder; Pydantic `max_length`; no request body reaches a log statement |
| VIII | Testability And Simplicity | Pure text functions, no live paid calls by default, simplest sufficient design | PASS | PASS — every `text_processing` function is `str → str` with no I/O; no database, no queue, no framework beyond FastAPI |

**Result: PASS on all eight gates, before and after design. Complexity Tracking is empty —
no deviation required justification.**

Two design choices are worth naming explicitly because they were made *to* satisfy gates
rather than in tension with them:

- The credential-free `edge` adapter exists because Principle V forbids claiming an
  unobserved pronunciation defect, and no defect can be observed on a provider that cannot
  be called. Without it, FR-019 would be unsatisfiable in this environment.
- Style is mapped to prosody and flagged as `approximated` rather than being reported as
  emotional synthesis, because Phase 0 established that Arabic voices expose no style
  parameter. Principle V forbids the stronger claim.

## Project Structure

### Documentation (this feature)

```text
specs/001-arabic-tts-prototype/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output — API + provider interface contracts
│   ├── http-api.md
│   └── provider-interface.md
├── checklists/
│   ├── requirements.md   # spec-quality (speckit-specify/clarify)
│   └── arabic-tts.md     # requirements-quality review (speckit-checklist)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, static mount, exception handlers
│   ├── config.py                   # Env-only settings (Pydantic Settings)
│   │
│   ├── api/
│   │   ├── tts.py                  # POST /api/tts, POST /api/tts/stream, /api/preview
│   │   ├── voices.py               # GET /api/voices, /api/providers, /api/locales
│   │   ├── benchmark.py            # POST /api/benchmark, GET /api/samples
│   │   └── pronunciation.py        # GET /api/pronunciation/demo, before/after audio
│   │
│   ├── providers/
│   │   ├── base.py                 # TTSProvider ABC, Capabilities, ProviderError
│   │   ├── edge.py                 # Microsoft Edge Neural TTS (credential-free)
│   │   ├── azure.py                # Azure AI Speech REST (credential-gated)
│   │   ├── elevenlabs.py           # ElevenLabs SSE streaming (credential-gated)
│   │   ├── fake.py                 # Deterministic test double (offline suite)
│   │   └── registry.py             # Availability-aware provider registry
│   │
│   ├── text_processing/
│   │   ├── pipeline.py             # Ordered stage composition + per-stage diff record
│   │   ├── arabic_normalizer.py    # Unicode NFC, tatweel, presentation forms, punctuation
│   │   ├── numbers.py              # Cardinals, decimals, percentages, identifier digits
│   │   ├── dates.py                # Numeric and mixed date verbalization
│   │   ├── currencies.py           # Amount + currency word order
│   │   ├── abbreviations.py        # Arabic and Latin abbreviations, initialisms
│   │   ├── code_switching.py       # Arabic/Latin span detection and handling
│   │   ├── pronunciation.py        # PronunciationRule application
│   │   ├── dictionary.py           # Rule data (names, brands, places, domain terms)
│   │   └── provider_formatting.py  # SSML construction with escaping
│   │
│   ├── services/
│   │   ├── tts_service.py          # Orchestration, fallback, trace assembly
│   │   ├── voice_router.py         # Dialect/locale/family → voice resolution
│   │   ├── benchmark_service.py    # Warm-up, repetitions, statistics, persistence
│   │   └── latency.py              # LatencyTrace, T0–T7 marks, derived metrics
│   │
│   ├── models/
│   │   ├── tts.py                  # TTSRequest, TTSResponse, ProcessedText, LatencyReport
│   │   ├── voice.py                # VoiceConfig, Dialect, EmotionStyle, AudioFormat
│   │   └── benchmark.py            # BenchmarkRun, BenchmarkResult, StageStats
│   │
│   └── data/
│       ├── voices.py               # Voice catalogue (16 Arabic locales)
│       └── samples.py              # Arabic evaluation sample set
│
└── tests/
    ├── unit/                       # Text processing, router, models, latency, statistics
    ├── contract/                   # Provider interface conformance, API schemas
    ├── integration/                # Live provider tests (credential-gated, marked)
    └── conftest.py

frontend/
└── index.html                      # Single static page: RTL textarea, selectors,
                                    # audio player, processed-text view, latency panel,
                                    # pronunciation before/after (no build step)

benchmarks/                         # Generated: results.json, <provider>.json, comparison.csv
docs/                               # TTS_EVALUATION.md, ARABIC_TEST_CASES.md,
                                    # PRONUNCIATION.md, BENCHMARK_RESULTS.md,
                                    # PRODUCTION_ARCHITECTURE.md, PROVIDER_RESEARCH_NOTES.md
.env.example
README.md
pyproject.toml
```

**Structure Decision**: Web-application layout (`backend/` + `frontend/`), chosen because the
feature has a genuine service boundary — a Python API that the demo page consumes over HTTP
and that the benchmark harness consumes directly. The single-project layout was rejected
because it would blur the boundary that Principle I exists to protect. The `frontend/`
directory holds exactly one file with no build step, keeping the asymmetry explicit: the
backend is the deliverable, the page is a window onto it.

Layering runs strictly one way — `api` → `services` → `providers` / `text_processing` →
`models`. `text_processing` imports nothing from `providers` or `services`, which is what
keeps its functions pure and testable offline.

## Design Decisions Carried Into Tasks

1. **Pipeline order is fixed and significant.** Dates and currencies run before the generic
   numbers stage, because the numbers stage's digit patterns are greedy and would otherwise
   consume a date's or amount's digits before the more specific stage ever saw them intact —
   caught by running the pipeline end-to-end during implementation (Constitution V), not
   assumed at planning time. Pronunciation rules run last so they can override any earlier
   stage's output. The pipeline records a per-stage before/after diff, satisfying FR-015 and
   FR-016 with the same mechanism.

2. **Routing is capability-driven, never name-driven.** `voice_router` resolves
   locale/dialect-family → `VoiceConfig`, then asks the provider's `Capabilities` whether it
   can serve the request. This is what makes SC-010 (add a provider, touch only its adapter)
   verifiable by an import-boundary test rather than by inspection alone.

3. **Fallback is per-request and recorded.** On timeout or provider error, `TTSService`
   attempts the voice's `fallback_voice_id` or the configured fallback provider, and marks
   the response so a substituted result is never mistaken for a primary one (FR-033).

4. **Streaming and non-streaming share one code path.** The non-streaming endpoint consumes
   the same async iterator and concatenates, so the two cannot drift.

5. **The pronunciation demo is generated, not authored.** A script synthesizes the candidate
   text, the defect is confirmed by listening, and only then is the case recorded with the
   voice and provider that exhibited it. Task ordering enforces this (T076 before T077).

## Complexity Tracking

No constitutional violations. No entries.
