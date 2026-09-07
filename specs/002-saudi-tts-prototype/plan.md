# Implementation Plan: Saudi Arabic TTS Prototype

**Branch**: `002-saudi-tts-prototype` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-saudi-tts-prototype/spec.md`

## Summary

Build a deliberately small Python service: Saudi Arabic text in, real Saudi-dialect speech
out, male or female voice selected, basic latency reported. The provider decision
(`research.md` R1) is settled by live evidence gathered before this plan was written: Groq's
`canopylabs/orpheus-arabic-saudi` — genuinely dialect-trained, six voices split by gender,
hosted, already implemented and tested in the prior feature (`001-arabic-tts-prototype`).
This plan **reuses that existing, working adapter** (`providers/base.py`, `providers/groq.py`
— chunking, WAV stitching, error mapping, bounded rate-limit retry) rather than rewriting
it, and **removes** everything the new spec puts out of scope: the multi-dialect voice
catalogue, the text-processing pipeline beyond Groq's own chunking need, the pronunciation
dictionary, diacritization/G2P, and the Hugging Face experimentation layer. This is a
subtraction-and-refocus, not a rebuild from zero.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from 001)

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic v2, httpx (async, for the Groq REST
call), pytest, pytest-asyncio. Everything else 001 added for HF/multi-provider work
(`huggingface_hub`, the optional `huggingface-local` extra, `edge-tts`) is dropped — this
feature has exactly one provider.

**Storage**: None. No database, no files beyond the running process's own logs.

**Testing**: pytest + pytest-asyncio. Offline unit tests against a `FakeProvider`; one
`@pytest.mark.integration` test makes a real Groq call, skipped without `GROQ_API_KEY`
(same tiering convention as 001, R9 in that feature's research.md).

**Target Platform**: Local machine (macOS/Linux), Python 3.12+, modern browser.

**Project Type**: Web service (Python backend) + one static HTML page, no build step.

**Performance Goals**: No formal target beyond FR-007's requirement that generation time,
audio duration, and real-time factor are always reported — this phase measures, it does not
yet optimize for a specific latency budget (that was 001's SC-002/SC-004, out of scope here).

**Constraints**: Requires `GROQ_API_KEY` (spec.md Assumptions — unlike 001's
credential-free default path, this phase's one provider needs a key); every provider call
carries an explicit timeout (FR-008); no Azure anywhere (FR-011).

**Scale/Scope**: Single concurrent user, prototype. Roughly 8-10 Python modules plus tests —
smaller than 001 by design (FR-012's explicit exclusions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

The repo constitution (`.specify/memory/constitution.md`) governs both features; nothing in
it is Saudi-TTS-specific, so gates are re-read against this narrower scope rather than
amended.

| # | Principle | Gate | Result |
|---|-----------|------|--------|
| I | Python-First Backend | All logic (voice resolution, latency measurement) lives in Python; the static page holds no domain logic | **PASS** — page only posts to `/api/speak` and renders the response |
| II | Provider Independence | Provider-specific code confined to an adapter behind an ABC; no domain branch on provider identity | **PASS** — `TTSProvider` ABC unchanged in shape from 001; only one adapter is registered, but nothing outside `providers/groq.py` names Groq |
| III | Arabic Linguistic Correctness | N/A at pipeline-stage scope for this feature (FR-012 removes the normalization/pronunciation pipeline) — the one thing that still applies is Groq's own 200-char chunking, which MUST NOT split mid-word | **PASS** — reuses 001's tested `_chunk_text`, unchanged, still word-boundary-safe |
| IV | Latency Is A Feature | Async I/O; latency measured and reported | **PASS** — FR-007; simplified to three `perf_counter` marks instead of 001's full T0-T7 trace, which this feature's spec does not require |
| V | Measured, Not Claimed | Every provider claim traced to a citation or an executed probe | **PASS** — FR-014; the Clarifications section records real, live evidence for every candidate, including the ones rejected |
| VI | Graceful Degradation | Explicit timeouts; provider failure never crashes the service | **PASS** — FR-008; single-provider means no cross-provider fallback exists for this phase (honest: SC-004 only requires a clear error, not a substitution) |
| VII | Secure By Default | Env-only credentials, no secret leakage, input length limits | **PASS** — reuses 001's `Settings`/no-secret-leak discipline |
| VIII | Testability And Simplicity | Simplest design that meets the requirement; no unjustified complexity | **PASS**, more strongly than 001 — this plan actively *removes* apparatus (dialect routing, pronunciation dictionary, HF layer) that FR-012 rules out of scope |

**Result: PASS on all eight gates.** Complexity Tracking is empty — every simplification in
this plan reduces complexity relative to 001, none adds it.

## Project Structure

### Documentation (this feature)

```text
specs/002-saudi-tts-prototype/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   └── http-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app, static mount, exception handlers
│   ├── config.py               # Env-only settings: GROQ_API_KEY, timeout, max chars
│   │
│   ├── api/
│   │   └── speak.py            # POST /api/speak, GET /api/voices
│   │
│   ├── providers/
│   │   ├── base.py             # TTSProvider ABC, ProviderError (reused from 001, trimmed)
│   │   ├── groq.py             # Orpheus Arabic adapter (reused from 001, unchanged)
│   │   └── fake.py             # Deterministic test double (reused from 001, trimmed)
│   │
│   ├── services/
│   │   └── latency.py          # Three-mark perf_counter trace + real-time factor
│   │
│   ├── models/
│   │   ├── voice.py             # Voice (id, name, provider, gender, dialect, model)
│   │   └── speech.py            # SpeechRequest, SpeechResponse, LatencyInfo
│   │
│   └── data/
│       └── voices.py            # The 6 Groq Saudi voices (3 male, 3 female)
│
└── tests/
    ├── unit/                    # FakeProvider-based: empty text, unknown voice, gender
    │                             # selection, provider-error handling
    ├── contract/                # test_no_secret_leak.py (reused pattern from 001)
    └── integration/              # One live Groq call, credential-gated
    └── conftest.py

frontend/
└── index.html                   # Single static page: textarea, gender toggle, voice
                                  # dropdown, Generate button, <audio>, latency readout
                                  # (no build step, no domain logic)

docs/
└── TTS_MODEL_EVALUATION.md      # The real comparison: Groq vs. the HF/ElevenLabs
                                  # candidates actually tested, with evidence

.env.example
requirements.txt                 # (or pyproject.toml, matching 001's convention)
README.md
```

**Structure Decision**: Same `backend/` + `frontend/` shape as 001 (a genuine service
boundary still exists — a Python API the page consumes over HTTP), but every module list is
shorter: no `text_processing/` package at all (FR-012), no `providers/huggingface/` or
`providers/elevenlabs.py`/`providers/edge.py` (single provider, FR-001's evidence-based
choice), no `data/dialect_profiles.py` or `data/pronunciation_dictionary.py`. Existing 001
modules that are directly reusable (`providers/base.py`, `providers/groq.py`,
`providers/fake.py`) are copied and trimmed of the multi-provider/multi-dialect fields this
feature's `Voice`/`Capabilities` shape does not need, not rewritten from scratch.

## Complexity Tracking

No constitutional violations. No entries — every change from 001 is a simplification.
