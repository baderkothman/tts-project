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
emotion control is portable across providers** — none of the three integrated adapters
declares phoneme support (ElevenLabs restricts phonemes to English, Groq's Orpheus Arabic
model accepts no markup at all, and the Edge client escapes all input), and no Arabic voice
in the catalogue exposes native speaking styles. Correction is therefore implemented as
provider-independent orthographic rewriting in Python, with markup-based control reserved
as a capability-gated enhancement for a future adapter that declares it. This is what keeps
the pipeline the asset rather than any vendor integration. (Azure is excluded from this
project by explicit mandate, not because it lacks SSML/phoneme support — see
`specs/001-arabic-tts-prototype/research.md` R1.)

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic v2, httpx (async, for Groq/ElevenLabs
REST and SSE), edge-tts (Microsoft Edge Neural TTS client), pytest, pytest-asyncio.
Hugging Face layer (research.md R10-R14): `huggingface_hub` unconditionally (lightweight
hosted-Inference-API client); `torch` + `transformers` added behind an optional
`[huggingface-local]` extra only once a specific small local model from the Model
Evaluation Matrix (R11) is actually wired up, so the credential-free Edge-only install
stays fast for anyone not exercising the HF path.

**Local hardware for on-device HF execution**: Apple M5, arm64, 24 GB unified memory, no
discrete GPU — measured via `sysctl`, not assumed (R10). This is the ceiling that routes
sub-~1B-parameter models to local MPS/CPU and everything larger to the hosted Inference
API by default (R12).

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
multi-tenant service. Roughly 25 Python modules plus tests, plus ~10 more for the Hugging
Face provider/linguistic-processing layer (below).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Gate | Initial | Post-Design |
|---|-----------|------|---------|-------------|
| I | Python-First Backend | All preprocessing, routing, benchmarking and metrics live in Python; frontend holds no domain logic | PASS | PASS — React is a typed presentation layer that posts requests, plays returned audio, and renders server decisions without duplicating linguistic or routing rules |
| II | Provider Independence | No provider SDK imported outside `providers/`; no domain branch on provider name | PASS | PASS — verified by design: `TTSProvider` ABC + `Capabilities` descriptor; router consults capability data, never a vendor name. Enforced by an automated import test (T082) |
| III | Arabic Linguistic Correctness | Hamza/taa-marbuta/alif-maqsura never folded; existing diacritics preserved; rules are data | PASS | PASS — `normalizer.py` explicitly excludes meaning-changing folds and documents why; `PronunciationRule` records are data loaded from a dictionary module |
| IV | Latency Is A Feature | Async throughout, streaming-first, TTFA instrumented | PASS | PASS — `async def` end to end; `StreamingResponse` forwards each chunk; `LatencyTrace` marks T0–T7 |
| V | Measured, Not Claimed | Every capability claim cited or executed; pronunciation defect actually observed | PASS | PASS — Phase 0 cites each claim; T076 **observes** the defect by synthesis before T077 documents it. The demo cannot be written before the observation step runs |
| VI | Graceful Degradation | Explicit timeouts, configured fallback, missing credentials → unavailable not crash | PASS | PASS — `TTSService` catches `ProviderError`/timeout and retries the fallback; `available()` is checked at registry build, never at import |
| VII | Secure By Default | Env-only secrets, no text/audio logging, length limits, injection prevented by construction | PASS | PASS — `config.py` reads env only; SSML built by an escaping builder; Pydantic `max_length`; no request body reaches a log statement |
| VIII | Testability And Simplicity | Pure text functions, no live paid calls by default, simplest sufficient design | PASS | PASS — every `text_processing` function is `str → str` with no I/O; no database, no queue, no framework beyond FastAPI |

**Result: PASS on all eight gates, before and after design. Complexity Tracking is empty —
no deviation required justification.**

**Re-checked for the Hugging Face dialect/pronunciation layer (US6-7, FR-048–FR-062):**

| # | Principle | How the HF layer satisfies it |
|---|-----------|-------------------------------|
| II | Provider Independence | HF synthesis lives behind the same provider interface as Edge/Groq/ElevenLabs (`providers/huggingface/`); HF dialect detection/diacritization/G2P are separate linguistic-processing services, not TTS — neither branches routing on "this is Hugging Face" (FR-060) |
| V | Measured, Not Claimed | research.md R11 is itself the enforcement mechanism for FR-058: nothing is downloaded before its license/size/relevance is recorded; FR-061/FR-062 require every dialect-improvement claim to cite a listening score, not a model card |
| VI | Graceful Degradation | An unavailable/oversized/timed-out HF model reports `unavailable` and falls through to an existing provider (FR-057), the same path already proven for Groq/ElevenLabs credential absence |
| VIII | Testability And Simplicity | Hosted-API-first (R12) is chosen specifically because it is the simpler default — no local model weights, no GPU code path — until a listening test justifies the added complexity of a local backend |

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
│   │   ├── pronunciation.py        # GET /api/pronunciation/demo, before/after audio
│   │   └── dialect.py              # POST /api/dialect/resolve, POST /api/dialect/compare
│   │                                # (US6/US7: detect-or-accept dialect; raw-vs-corrected
│   │                                # comparison for arbitrary text, not only the fixed demo)
│   │
│   ├── providers/
│   │   ├── base.py                 # TTSProvider ABC, Capabilities, ProviderError
│   │   ├── edge.py                 # Microsoft Edge Neural TTS (credential-free)
│   │   ├── groq.py                 # Groq Orpheus Arabic — Saudi dialect (credential-gated)
│   │   ├── elevenlabs.py           # ElevenLabs SSE streaming (credential-gated)
│   │   ├── fake.py                 # Deterministic test double (offline suite)
│   │   ├── registry.py             # Availability-aware provider registry
│   │   └── huggingface/            # FR-060: HF synthesis behind the same TTSProvider ABC
│   │       ├── provider.py         #   Adapter; picks an execution backend per HFModelConfig
│   │       ├── local.py            #   MPS/CPU backend (small models only — R10 ceiling)
│   │       ├── inference_api.py    #   Hosted Inference API backend (default — R12)
│   │       ├── endpoint.py         #   Dedicated Inference Endpoint backend (documented,
│   │       │                       #   not wired to any model by default — R12)
│   │       └── models.py           #   Request/response/config dataclasses for this package
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
│   │   ├── provider_formatting.py  # SSML construction with escaping
│   │   └── huggingface/            # FR-060: separate from TTS; independently testable
│   │       ├── dialect_classifier.py  # FR-048: text-in dialect detection (R13)
│   │       ├── diacritizer.py         # FR-052/053: diacritization backend calls
│   │       ├── g2p.py                 # Phoneme representation for the pronunciation dict
│   │       ├── pronunciation_model.py # FR-052: dictionary lookup + dialect scoping
│   │       └── model_registry.py      # FR-055: reads HFModelConfig, no hardcoded models
│   │
│   ├── services/
│   │   ├── tts_service.py          # Orchestration, fallback, trace assembly
│   │   ├── voice_router.py         # Dialect/locale/family → voice resolution
│   │   ├── benchmark_service.py    # Warm-up, repetitions, statistics, persistence
│   │   ├── latency.py              # LatencyTrace, T0–T7 marks, derived metrics
│   │   └── dialect_service.py      # FR-048/FR-053: resolves dialect (user > classifier),
│   │                                # assembles the raw-vs-corrected comparison result
│   │
│   ├── models/
│   │   ├── tts.py                  # TTSRequest, TTSResponse, ProcessedText, LatencyReport
│   │   ├── voice.py                # VoiceConfig, Dialect, EmotionStyle, AudioFormat
│   │   ├── benchmark.py            # BenchmarkRun, BenchmarkResult, StageStats
│   │   └── dialect.py              # DialectProfile, PronunciationDictionaryEntry,
│   │                                # HFModelConfig, DialectDetectionResult
│   │
│   └── data/
│       ├── voices.py                    # Voice catalogue (16 Arabic locales)
│       ├── samples.py                   # Arabic evaluation sample set
│       ├── dialect_profiles.py          # FR-049: msa/levantine/lebanese/gulf/saudi/egyptian
│       ├── pronunciation_dictionary.py  # FR-052: token-level entries (distinct from the
│       │                                # existing pattern-matched dictionary.py rules)
│       └── hf_model_registry.py         # FR-055/FR-058: the Model Evaluation Matrix
│                                         # (research.md R11) as loadable HFModelConfig data
│
└── tests/
    ├── unit/                       # Text processing, router, models, latency, statistics,
    │                                # + dialect resolution, pronunciation dict, HF registry
    ├── contract/                   # Provider interface conformance, API schemas
    ├── integration/                # Live provider tests (credential-gated, marked),
    │                                # + live HF calls gated on HF_TOKEN
    └── conftest.py

frontend/
├── src/                            # React + TypeScript presentation components,
│                                   # typed API adapter, RTL styles, and frontend tests
├── index.html                      # Vite application shell
├── package.json                    # Development, test, type-check, and build commands
└── dist/                           # Generated production assets served by FastAPI

benchmarks/                         # Generated: results.json, <provider>.json, comparison.csv
docs/                               # TTS_EVALUATION.md, DIALECT_EVALUATION.md,
                                    # VOICE_CATALOG.md, ARABIC_TEST_CASES.md,
                                    # PRONUNCIATION.md, BENCHMARK_RESULTS.md,
                                    # PRODUCTION_ARCHITECTURE.md, PROVIDER_RESEARCH_NOTES.md,
                                    # HF_MODEL_RESEARCH.md, PRONUNCIATION_EVALUATION.md
.env.example
README.md
pyproject.toml
```

**Structure Decision**: Web-application layout (`backend/` + `frontend/`), chosen because the
feature has a genuine service boundary — a Python API consumed over HTTP by both the React
presentation layer and the benchmark harness. The typed frontend adapter mirrors the HTTP
contract but owns no provider, routing, or linguistic decisions. Vite emits static assets to
`frontend/dist`, which FastAPI serves in the single-server production path.

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

6. **The Hugging Face model registry is the only place a specific `repo_id` is named.**
   `hf_model_registry.py` holds the R11 Model Evaluation Matrix as data (`HFModelConfig`);
   `dialect_service.py`, the HF provider adapter, and the linguistic-processing services all
   read from it. This is what makes swapping `oddadmix/chatterbox-egyptian-v0` for a later,
   better-verified Egyptian model a data change, not an application-logic change — the same
   discipline Decision 2 already applies to provider routing.

7. **Dialect resolution always tries user selection before the classifier, and both are
   still returned.** `dialect_service.resolve()` returns a `DialectDetectionResult`
   carrying whichever path was used and, when the classifier ran, its raw label and
   confidence — never silently discarding the classifier's actual output even when the
   user's selection overrides it, so FR-051's honesty requirement is structural rather than
   a formatting convention applied at the last step.

8. **The raw-vs-corrected comparison and the fixed pronunciation demo share one code path.**
   `GET /api/pronunciation/demo` (Story 5) becomes a call to the same comparison assembly
   `POST /api/dialect/compare` (Story 7) uses, with the demo's fixed sample as input — so
   the two cannot drift apart and Story 7's generality is verified by construction rather
   than by keeping two implementations in sync by hand.

## Complexity Tracking

No constitutional violations. No entries.
