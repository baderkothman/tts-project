---

description: "Task list for Saudi Arabic TTS Prototype"
---

# Tasks: Saudi Arabic TTS Prototype

**Input**: Design documents from `/specs/002-saudi-tts-prototype/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — FR-004/FR-005/FR-008 require behavior that must be verifiable
offline (Constitution VIII), matching this project's established pattern.

**Organization**: Tasks grouped by user story (US1 P1, US2 P2), preceded by Setup/
Foundational, followed by Polish — which includes the deletion of everything spec.md's
FR-012 puts out of scope. Deletion is a **separate, explicit phase**, not folded into
Setup, so the removal itself is inspectable and traceable to the requirement that drives it.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create `backend/app/{api,providers,services,models,data}/`, `backend/tests/{unit,contract,integration}/`, `frontend/`, `docs/` — new, minimal tree per plan.md (does not touch 001's existing tree yet — that happens in Phase 6)
- [X] T002 Update `pyproject.toml`: keep `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`; remove `edge-tts`, `huggingface_hub`, and the `huggingface-local` extra (no longer used by this feature)
- [X] T003 [P] Rewrite `.env.example`: `GROQ_API_KEY` only, with a one-line comment that this phase has no credential-free path
- [X] T004 [P] Confirm `pyproject.toml`'s `[tool.pytest.ini_options]` `integration` marker still registered (reused from 001, no change needed)

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T005 [P] Implement `backend/app/config.py` — `Settings` with `groq_api_key`, `request_timeout_s`, `max_input_chars` only (trimmed from 001's `Settings`)
- [X] T006 [P] Implement `backend/app/models/voice.py` — `Voice` (id, name, provider, gender: Literal["male","female","unknown"], dialect="saudi", model) per data-model.md
- [X] T007 [P] Implement `backend/app/models/speech.py` — `SpeechRequest`, `SpeechResponse`, `LatencyInfo` per data-model.md, with the empty/whitespace-text validator (FR-004)
- [X] T008 Implement `backend/app/providers/base.py` — `TTSProvider` ABC (`synthesize`, `list_voices`) and `ProviderError` — trimmed copy of 001's, dropping `Capabilities`/`ProviderRequest` fields this feature's single provider doesn't need (streaming flags, SSML, emotion)
- [X] T009 [P] Implement `backend/app/providers/fake.py` — deterministic `FakeProvider` (configurable failure kind) for offline tests, trimmed from 001's
- [X] T010 Implement `backend/app/data/voices.py` — the 6 real Groq Saudi voices (male: Abdullah, Fahad, Sultan; female: Lulwa, Noura, Aisha), `model="canopylabs/orpheus-arabic-saudi"` on every entry
- [X] T011 Implement `backend/app/providers/groq.py` — port 001's adapter (`_chunk_text`, `_concat_wav`, 401/429/5xx mapping, bounded rate-limit retry) unchanged in logic, adapted to this feature's smaller `Voice`/`ProviderError` shape (research.md R2)
- [X] T012 Implement `backend/app/services/latency.py` — three-mark `perf_counter` trace (`request_received`, `provider_call_started`, `audio_received`) plus `LatencyInfo` derivation (generation_ms, audio_duration_ms via WAV frame count, real_time_factor)
- [X] T013 Implement `backend/app/main.py` — FastAPI app, static mount for `frontend/`, `/health` reporting `provider_available`
- [X] T014 [P] Write `backend/tests/conftest.py` — FastAPI `TestClient` fixture, `FakeProvider`-backed registry override

**Checkpoint**: Foundation ready — US1 and US2 may proceed.

---

## Phase 3: User Story 1 — Hear Saudi Arabic Speech, Male or Female Voice (Priority: P1) 🎯 MVP

**Goal**: Saudi Arabic text in, streaming-free but real audio out, correct gender served.

**Independent Test**: Submit a Saudi sentence with `gender=male`, then `gender=female`;
confirm both produce real, distinctly-gendered audio.

- [X] T015 [P] [US1] Write `backend/tests/unit/test_voice_resolution.py` — `voice_id` explicit selection, `gender` default resolution, unknown `voice_id` raises with valid alternatives named (FR-005)
- [X] T016 [P] [US1] Write `backend/tests/unit/test_groq_provider.py` — port the relevant subset of 001's tests (chunking word-boundary safety, WAV stitching, 401/429/5xx mapping) using `httpx.MockTransport`, no live calls
- [X] T017 [US1] Implement voice resolution (`voice_id` > `gender` default > reject) in `backend/app/services/voice_resolution.py`
- [X] T018 [US1] Implement `GET /api/voices` in `backend/app/api/speak.py`
- [X] T019 [US1] Implement `POST /api/speak` in `backend/app/api/speak.py` — resolve voice → call provider → assemble `SpeechResponse`, mapping `ProviderError` to `400`/`502` per contracts/http-api.md
- [X] T020 [P] [US1] Write `backend/tests/contract/test_api_speak.py` covering AC-01 (empty text → 422), AC-02 (unknown voice → 400 with alternatives), AC-03 (male → `voice.gender=="male"`), AC-04 (female → `voice.gender=="female"`)
- [X] T021 [US1] Create `frontend/index.html` — Saudi Arabic textarea, gender toggle, voice dropdown (populated from `/api/voices`, filtered by gender), Generate button, `<audio>` player — no build step, no domain logic (Constitution I)
- [X] T022 [P] [US1] Write `backend/tests/integration/test_live_groq.py::test_male_and_female_voice_live` — `@pytest.mark.integration`, skipped without `GROQ_API_KEY`, otherwise a real call for one male and one female voice, asserting non-empty audio for both

**Checkpoint**: MVP — Saudi Arabic text produces real, correctly-gendered speech.

---

## Phase 4: User Story 2 — See How Long Generation Took (Priority: P2)

**Goal**: Every response reports generation time, audio duration, and real-time factor.

**Independent Test**: Generate speech; confirm `latency.generation_ms`,
`latency.audio_duration_ms`, `latency.real_time_factor` are all present and numeric.

- [X] T023 [P] [US2] Write `backend/tests/unit/test_latency.py` — real-time-factor arithmetic on known synthetic durations, and a WAV-duration-from-frame-count helper test
- [X] T024 [US2] Wire `LatencyTrace` into `POST /api/speak`'s handler (depends on T012, T019) so every successful response carries a complete `LatencyInfo`
- [X] T025 [P] [US2] Write `backend/tests/contract/test_api_speak.py::test_latency_always_present` (AC-05)
- [X] T026 [US2] Add the latency readout (generation time, audio duration, RTF) to `frontend/index.html`
- [X] T027 [US2] Write `backend/tests/unit/test_provider_error_handling.py` — induced timeout/rate-limit/server error via `FakeProvider` maps to `502` with a clear, distinguishable `detail`, never a crash (FR-008, AC-07)

**Checkpoint**: Both user stories complete and independently testable.

---

## Phase 5: Polish

- [X] T028 [P] Write `backend/tests/contract/test_no_secret_leak.py` — no credential value in any response body, header, or error message (reused pattern from 001)
- [X] T029 [P] Write `docs/TTS_MODEL_EVALUATION.md` from research.md R1 — the real comparison table and per-candidate evidence (Groq selected; NAMAA-Saudi-TTS, NAMAA-Saudi-TTS-V2, Magpie-TTS-Saudi-Arabic, ElevenLabs all tested/checked live and not selected, each with its specific reason)
- [X] T030 Write `README.md` — exact setup/run commands, `.env.example` reference, known limitations (single provider, single gender's worth of voices per model actually verified live for male vs. female timbre — the rest inferred from vendor voice naming)
- [X] T031 Run `.venv/bin/pytest backend/tests -v -m "not integration"` and confirm it passes fully offline
- [X] T032 Execute quickstart.md V1–V7 end to end against the running app and record actual outcomes (Constitution V)

---

## Phase 6: Remediation — remove out-of-scope modules from the active codebase (FR-012)

**Purpose**: spec.md FR-012 explicitly excludes pronunciation correction, diacritization,
G2P, pronunciation dictionaries, multi-dialect routing, STT, LLM integration, avatars, and
the multi-stage text-processing pipeline. This phase removes the corresponding 001 modules
from the active codebase rather than leaving them present-but-unused, per the brief's
explicit "remove, do not carry forward" instruction. `specs/001-arabic-tts-prototype/` and
its own `docs/`-referenced historical record are **not** touched — this phase removes code,
not the record of the prior phase's work.

- [X] T033 Remove `backend/app/text_processing/` in its entirety (normalization, numbers, dates, currencies, abbreviations, code-switching, pronunciation rules, the Hugging Face linguistic-processing submodule)
- [X] T034 Remove `backend/app/providers/edge.py`, `backend/app/providers/elevenlabs.py`, `backend/app/providers/huggingface/` (this feature has one provider: Groq)
- [X] T035 Remove `backend/app/services/voice_router.py`, `backend/app/services/dialect_service.py`, `backend/app/services/benchmark_service.py`, `backend/app/services/tts_service.py` (superseded by `services/voice_resolution.py` + inline orchestration in `api/speak.py`)
- [X] T036 Remove `backend/app/data/dialect_profiles.py`, `backend/app/data/pronunciation_dictionary.py`, `backend/app/data/hf_model_registry.py`, `backend/app/data/samples.py`, and 001's `backend/app/data/voices.py` (replaced by T010's minimal Saudi-only version)
- [X] T037 Remove `backend/app/models/dialect.py`, and trim `backend/app/models/tts.py`/`backend/app/models/voice.py` down to nothing (replaced by `models/voice.py` + `models/speech.py` from Phase 2)
- [X] T038 Remove `backend/app/api/dialect.py`, `backend/app/api/pronunciation.py`, `backend/app/api/benchmark.py`, and 001's `backend/app/api/tts.py`/`backend/app/api/voices.py` (replaced by `api/speak.py`)
- [X] T039 Remove 001's entire `backend/tests/` tree (unit/contract/integration files exercising the removed modules) after Phase 3-5's new tests are confirmed passing, so the offline suite is never left broken mid-removal
- [X] T040 Remove `docs/DIALECT_EVALUATION.md`, `docs/HF_MODEL_RESEARCH.md`, `docs/PRONUNCIATION_EVALUATION.md`, `docs/PRONUNCIATION.md`, `docs/BENCHMARK_RESULTS.md`, `docs/VOICE_CATALOG.md`, `docs/PROVIDER_RESEARCH_NOTES.md`, `docs/PRODUCTION_ARCHITECTURE.md`, `docs/ARABIC_TEST_CASES.md`, `docs/TTS_EVALUATION.md`, `docs/audio/` (all superseded by this feature's much narrower scope and `docs/TTS_MODEL_EVALUATION.md`)
- [X] T041 Remove `frontend/src/`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/node_modules/`, `frontend/dist/` (the parallel session's React/Vite rebuild) — replaced by this feature's single static `frontend/index.html`
- [X] T042 Remove `benchmarks/` (the multi-provider benchmark harness and its output — no benchmarking apparatus in this feature beyond the three-mark latency trace)
- [X] T043 Remove `scripts/observe_pronunciation.py`, `scripts/observe_dialect_tts.py` (both exercise removed modules)
- [X] T044 Update `README.md` and `.gitignore` to remove references to removed directories (`frontend/dist`, `frontend/node_modules`, `benchmarks/`, `docs/audio/`)
- [X] T045 Re-run `.venv/bin/pytest backend/tests -v -m "not integration"` and confirm the suite is clean — only this feature's tests remain, all passing

**Checkpoint**: The active codebase matches spec.md's scope exactly — nothing FR-012
excludes is still present and reachable.

---

## Dependencies

```text
Phase 1 Setup
   └─> Phase 2 Foundational (blocks everything)
          ├─> Phase 3 US1 (P1) — MVP
          │      └─> Phase 4 US2 (P2) — needs US1's /api/speak to attach latency to
          └─> Phase 5 Polish (needs US1+US2 complete to document/validate honestly)
                 └─> Phase 6 Remediation (deletion happens LAST, only once the new,
                     smaller system is proven working and tested — never delete the old
                     before the new replacement is confirmed functional)
```

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1)**. Phase 6 (deletion) is deliberately the very
last phase — the new minimal system must be built, tested, and confirmed working *before*
the old, broader system is removed, so there is never a window where neither works.
