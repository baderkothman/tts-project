---

description: "Task list for Arabic Text-to-Speech Prototype"
---

# Tasks: Arabic Text-to-Speech Prototype

**Input**: Design documents from `/specs/001-arabic-tts-prototype/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks ARE included — the specification mandates them (FR-016, SC-015) and the
constitution requires offline-capable verification (Principle VIII).

**Organization**: Tasks are grouped by user story so each story is independently implementable
and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task serves (US1–US5)
- Exact file paths are given in every task

## Path Conventions

Web-app layout per plan.md: `backend/app/`, `backend/tests/`, `frontend/`, `benchmarks/`, `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and structure

- [X] T001 Create the directory tree from plan.md under `backend/app/`, `backend/tests/`, `frontend/`, `benchmarks/`, `docs/`, with `__init__.py` in every Python package
- [X] T002 Create `pyproject.toml` declaring Python 3.12, runtime deps (fastapi, uvicorn, pydantic, pydantic-settings, httpx, edge-tts) and a `dev` extra (pytest, pytest-asyncio)
- [X] T003 [P] Create `.env.example` listing `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `ELEVENLABS_API_KEY`, `TTS_DEFAULT_PROVIDER`, `TTS_FALLBACK_PROVIDER`, `TTS_REQUEST_TIMEOUT_S`, `TTS_MAX_INPUT_CHARS` — names only, no values (FR-039)
- [X] T004 [P] Create `.gitignore` excluding `.venv/`, `.env`, `__pycache__/`, and generated audio
- [X] T005 [P] Configure pytest in `pyproject.toml`: asyncio mode, and register the `integration` marker used to gate credentialed tests (R9)
- [X] T006 [P] Create `backend/tests/conftest.py` with shared fixtures: FastAPI test client, `FakeProvider` registry override, and Arabic sample fixtures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Contracts and core types every user story depends on. **No user story can start until this phase completes.**

- [X] T007 [P] Implement `backend/app/config.py` — Pydantic Settings reading env only, with input-length limit, per-call timeout, default/fallback provider (FR-039, FR-032)
- [X] T008 [P] Implement enums in `backend/app/models/voice.py`: `Dialect`, `EmotionStyle`, `AudioFormat`, `ProviderStatus` per data-model.md
- [X] T009 [P] Implement `VoiceConfig` in `backend/app/models/voice.py` with nullable `dialect` so "no documented dialect" is representable (FR-027)
- [X] T010 Implement `TTSRequest` in `backend/app/models/tts.py` with all validation rules from data-model.md, including strip-then-min-length and `max_length` (FR-003, FR-042)
- [X] T011 Implement `ProcessedText`, `StageDiff`, `LatencyReport`, `TTSResponse` in `backend/app/models/tts.py` (FR-015, FR-031)
- [X] T012 [P] Implement `BenchmarkRun`, `BenchmarkResult`, `StageStats`, `ArabicSample` in `backend/app/models/benchmark.py` (FR-035–FR-038a)
- [X] T013 [P] Implement `PronunciationRule` and `PronunciationDemo` in `backend/app/models/tts.py`, with `provider_observed`/`voice_observed` required (FR-019)
- [X] T014 Implement `backend/app/providers/base.py` — `TTSProvider` ABC, `Capabilities`, `ProviderRequest`, and `ProviderError` with `kind`/`retryable` per contracts/provider-interface.md
- [X] T015 Implement `backend/app/services/latency.py` — `LatencyTrace` with `perf_counter` marks T0–T7 and derived-metric computation (R6, FR-031)
- [X] T016 [P] Implement `backend/app/providers/fake.py` — deterministic `FakeProvider` supporting configurable chunk count, delay, timeout and mid-stream failure (R9)
- [X] T017 Implement `backend/app/providers/registry.py` — availability-aware registry that never raises at import when credentials are absent (FR-024, FR-034)
- [X] T018 Implement `backend/app/data/voices.py` — voice catalogue for the 16 Arabic locales with dialect-family mapping and fallback voice ids (FR-027, R2)
- [X] T019 Implement `backend/app/main.py` — FastAPI app, static mount for `frontend/`, `/health`, and exception handlers mapping `ProviderError` to HTTP status without leaking secrets (FR-039)
- [X] T020 [P] Write `backend/tests/unit/test_models.py` covering every validation rule in data-model.md (FR-003, FR-042)
- [X] T021 [P] Write `backend/tests/contract/test_provider_conformance.py` implementing PC-01…PC-12 against all registered providers

**Checkpoint**: Foundation ready — user stories may proceed.

---

## Phase 3: User Story 1 — Hear Arabic Text Spoken Aloud (Priority: P1) 🎯 MVP

**Goal**: Arabic text in, streaming Arabic speech out.

**Independent Test**: Submit an MSA paragraph; hear intelligible Arabic that begins playing before synthesis completes.

- [X] T022 [P] [US1] Write `backend/tests/unit/test_edge_provider.py` asserting the Edge adapter declares streaming and yields multiple chunks (uses recorded/fake transport offline)
- [X] T023 [US1] Implement `backend/app/providers/edge.py` — Edge Neural TTS adapter with `synthesize`, `stream`, `get_voices`, `capabilities`, mapping failures to `ProviderError` (R1, PC-06)
- [X] T024 [US1] Declare Edge `Capabilities`: streaming true, ssml false, phoneme false, native_emotions **false**, prosody rate/pitch/volume true, 16 Arabic locales (R2, R3)
- [X] T025 [US1] Implement `backend/app/services/voice_router.py` — resolve locale / dialect family / explicit voice to a `VoiceConfig`, rejecting mismatches with alternatives named (FR-025, FR-025a, FR-026)
- [X] T026 [US1] Implement `backend/app/services/tts_service.py` — orchestrate route → preprocess → synthesize, assembling the `LatencyTrace` (FR-031)
- [X] T027 [US1] Implement `POST /api/tts` in `backend/app/api/tts.py` returning `TTSResponse` (FR-030)
- [X] T028 [US1] Implement `POST /api/tts/stream` in `backend/app/api/tts.py` using `StreamingResponse`, writing each chunk on arrival and setting `X-TTS-*` headers before the first byte (FR-029, contracts/http-api.md)
- [X] T029 [P] [US1] Write `backend/tests/unit/test_streaming.py` asserting the first chunk is emitted before the stream completes and that chunks are not accumulated (AC-07, SC-002)
- [X] T030 [P] [US1] Write `backend/tests/contract/test_api_tts.py` covering AC-01, AC-02, AC-10
- [X] T031 [US1] Create `frontend/index.html` — RTL Arabic textarea, Generate button, `<audio>` element pointed at the streaming endpoint, no build step, no domain logic (Principle I)

**Checkpoint**: MVP — Arabic text produces streaming Arabic speech.

---

## Phase 4: User Story 2 — Correct Pronunciation of Difficult Arabic Text (Priority: P1)

**Goal**: Numbers, dates, currencies, abbreviations, code-switching and difficult words are spoken as correct Arabic.

**Independent Test**: Submit the difficult-content sample set to `/api/preview`; every category matches its stated expected transformation, with no provider call.

- [X] T032 [P] [US2] Write `backend/tests/unit/test_arabic_normalizer.py` — asserts tatweel/presentation-form/punctuation handling AND asserts hamza, taa marbuta and alif maqsura are **preserved**, plus diacritic preservation (FR-006, FR-007, FR-008)
- [X] T033 [US2] Implement `backend/app/text_processing/arabic_normalizer.py` — NFC, control/invisible character removal, tatweel, presentation forms, punctuation; explicitly no meaning-changing folds, documented inline (Principle III)
- [X] T034 [P] [US2] Write `backend/tests/unit/test_numbers.py` for cardinals, decimals, percentages and identifier digit strings (FR-009, FR-014)
- [X] T035 [US2] Implement `backend/app/text_processing/numbers.py` — Arabic cardinal verbalization with gender/case handling, decimals, percentages, and digit-sequence mode for identifiers (FR-009, FR-014)
- [X] T036 [P] [US2] Write `backend/tests/unit/test_dates.py` for `27/09/2026`, `2026-09-27`, `27 سبتمبر 2026` (FR-010)
- [X] T037 [US2] Implement `backend/app/text_processing/dates.py` — numeric and mixed date verbalization with Arabic month names (FR-010)
- [X] T038 [P] [US2] Write `backend/tests/unit/test_currencies.py` for `$25`, `25 USD`, `100 ريال`, `1,250.50 دولار` (FR-011)
- [X] T039 [US2] Implement `backend/app/text_processing/currencies.py` — symbol and code recognition, amount-then-currency Arabic word order, subunit handling (FR-011)
- [X] T040 [P] [US2] Write `backend/tests/unit/test_abbreviations.py` for `د.`, `م.`, `API`, `AWS`, `AI`, `CEO` (FR-012)
- [X] T041 [US2] Implement `backend/app/text_processing/abbreviations.py` — Arabic abbreviation expansion plus initialisms distinguished from read-as-word acronyms (FR-012)
- [X] T042 [P] [US2] Write `backend/tests/unit/test_code_switching.py` for the Arabic/English mixed sentence (FR-013)
- [X] T043 [US2] Implement `backend/app/text_processing/code_switching.py` — Arabic/Latin span detection preserving sentence flow (FR-013)
- [X] T044 [P] [US2] Write `backend/tests/unit/test_pronunciation.py` including a whole-word-boundary case proving a rule does not fire inside a longer prefixed word (FR-017, CHK022)
- [X] T045 [US2] Implement `backend/app/text_processing/dictionary.py` — rule data for names, companies, places, products, medical, banking, foreign terms (FR-018)
- [X] T046 [US2] Implement `backend/app/text_processing/pronunciation.py` — apply rules filtered by locale and provider, honouring `whole_word` (FR-017)
- [X] T047 [US2] Implement `backend/app/text_processing/provider_formatting.py` — SSML built programmatically with **all interpolated text escaped**; phoneme tags emitted only when `capabilities.phoneme` (FR-041, R4)
- [X] T048 [P] [US2] Write `backend/tests/unit/test_ssml_injection.py` — SSML-like user text is escaped and cannot alter instructions (FR-041, AC-05, SC-012)
- [X] T049 [US2] Implement `backend/app/text_processing/pipeline.py` — fixed stage order (normalize → numbers → dates → currencies → abbreviations → code-switching → pronunciation → provider formatting) recording a `StageDiff` per stage (FR-015, FR-016)
- [X] T050 [US2] Wire the pipeline into `tts_service`, honouring `apply_preprocessing` and `apply_pronunciation` independently (FR-020)
- [X] T051 [US2] Implement `POST /api/preview` in `backend/app/api/tts.py` returning `ProcessedText` with stage diffs and no provider call (FR-015)
- [X] T052 [P] [US2] Write `backend/tests/unit/test_pipeline_order.py` — asserts numbers run before dates and pronunciation runs last, since order changes output
- [X] T053 [US2] Add the raw-vs-processed text panel to `frontend/index.html` (FR-015)

**Checkpoint**: Difficult Arabic content is verbalized correctly and inspectably.

---

## Phase 5: User Story 3 — Compare Providers, Voices, Dialects and Styles (Priority: P2)

**Goal**: Multiple providers, dialects and styles are selectable and comparable.

**Independent Test**: Render one sentence across providers, two locales and two styles; results differ or are honestly reported unsupported.

- [X] T054 [P] [US3] Write `backend/tests/unit/test_voice_router.py` — dialect-family resolution, unsupported locale, voice/provider mismatch (FR-025a, FR-026, AC-03, AC-04)
- [X] T055 [US3] Implement `backend/app/providers/azure.py` — Azure Speech REST adapter with SSML, `<phoneme>` support, streaming, credential-gated `available()` (R1, R4)
- [X] T056 [US3] Declare Azure `Capabilities`: ssml true, phoneme true, **native_emotions false for Arabic** with the reason documented inline (R2, R3)
- [X] T057 [US3] Implement `backend/app/providers/elevenlabs.py` — ElevenLabs adapter with SSE streaming, voice-settings style mapping, credential-gated `available()` (R1, R3)
- [X] T058 [US3] Declare ElevenLabs `Capabilities` with an **empty dialect set** and phoneme false for Arabic, documenting that phoneme tags are English-only (R2, R4, FR-027)
- [X] T059 [US3] Implement style→prosody mapping shared by Edge and Azure, setting `emotion_native=False` when approximated (FR-028, R3)
- [X] T060 [US3] Implement fallback in `tts_service` — on retryable `ProviderError`, attempt fallback voice/provider and set `used_fallback` + `fallback_reason` (FR-033)
- [X] T061 [P] [US3] Write `backend/tests/unit/test_fallback.py` — induced timeout and provider error produce fallback or actionable error, never a crash (FR-033, FR-034, AC-08, AC-09, SC-009)
- [X] T062 [P] [US3] Write `backend/tests/unit/test_provider_availability.py` — missing credentials yield `missing_credentials`, not an exception (FR-024)
- [X] T063 [US3] Implement `GET /api/providers`, `GET /api/voices`, `GET /api/locales` in `backend/app/api/voices.py` (FR-023, FR-024)
- [X] T064 [US3] Add provider, voice, dialect and style selectors to `frontend/index.html`, showing unavailable providers with their reason
- [X] T065 [P] [US3] Write `backend/tests/integration/test_live_providers.py` marked `@pytest.mark.integration`, skipped without credentials (R9, SC-015)

**Checkpoint**: Provider, dialect and style comparison works; unavailable providers degrade honestly.

---

## Phase 6: User Story 4 — Measure and Compare Latency (Priority: P2)

**Goal**: Per-stage latency per request, and repeatable benchmarks persisted as files.

**Independent Test**: Run the benchmark; statistics files appear with min/max/mean/median/P95 per stage.

- [X] T066 [P] [US4] Write `backend/tests/unit/test_latency.py` — T0–T7 marks produce correct derived metrics, and `client_ttfa_ms` is null without a client T0 (R6)
- [X] T067 [US4] Implement `backend/app/data/samples.py` — the Arabic sample set across all nine categories, each difficult-content sample carrying its expected transformation (FR-038, FR-038a)
- [X] T068 [P] [US4] Write `backend/tests/unit/test_samples.py` — asserts every difficult-content sample's expected transformation actually holds through the pipeline (SC-003, FR-038a)
- [X] T069 [P] [US4] Write `backend/tests/unit/test_statistics.py` — min/max/mean/median and nearest-rank P95 on known inputs (FR-036, R7)
- [X] T070 [US4] Implement `backend/app/services/benchmark_service.py` — discarded warm-up, N repetitions, per-stage statistics, real-time factor, recording `warmup_discarded` (FR-035–FR-037, R7)
- [X] T071 [US4] Implement benchmark persistence writing `benchmarks/<provider>.json`, `benchmarks/results.json` and `benchmarks/comparison.csv` with provider, voice, sample set and timestamp (FR-037)
- [X] T072 [US4] Add a CLI entry point to `benchmark_service.py` so benchmarks run without the HTTP server (quickstart V7)
- [X] T073 [US4] Implement `POST /api/benchmark` and `GET /api/samples` in `backend/app/api/benchmark.py` (FR-035, FR-038)
- [X] T074 [P] [US4] Write `backend/tests/unit/test_pipeline_performance.py` — preprocessing P95 under 50 ms for 500 characters (SC-004)
- [X] T075 [US4] Add the latency metrics panel to `frontend/index.html` showing each stage and the real-time factor (FR-031)

**Checkpoint**: Latency is measured per request and benchmarked reproducibly.

---

## Phase 7: User Story 5 — Demonstrate a Pronunciation Fix Before and After (Priority: P3)

**Goal**: A genuinely observed defect, corrected, with before/after audio.

**Independent Test**: Play both renderings of the same source text and hear the described difference.

> **Ordering is mandatory**: T076 must produce a real observation before T077 records it.
> Constitution Principle V and FR-019 forbid documenting an unobserved defect.

- [X] T076 [US5] Create `scripts/observe_pronunciation.py` and **run it** — synthesize candidate cases (ambiguous undiacritized words, foreign brand names, Latin initialisms) and record which actually mispronounce, with the provider and voice used (FR-019, Principle V)
- [X] T077 [US5] Record the confirmed defect in `backend/app/text_processing/dictionary.py` as a `PronunciationDemo` plus its correcting rule, using only cases observed in T076 (FR-019)
- [X] T078 [US5] Implement `GET /api/pronunciation/demo` and `GET /api/pronunciation/demo/audio?corrected=` in `backend/app/api/pronunciation.py` (FR-020)
- [X] T079 [P] [US5] Write `backend/tests/unit/test_pronunciation_demo.py` — corrected and uncorrected paths yield different processed text from identical source (FR-020)
- [X] T080 [US5] Add the before/after comparison panel with two audio players to `frontend/index.html`
- [X] T081 [US5] Save both renderings to `docs/audio/` as durable evidence for the documentation

**Checkpoint**: All five user stories complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T082 [P] Write `backend/tests/contract/test_import_boundaries.py` — asserts no provider SDK is imported outside `backend/app/providers/` and no domain module branches on a provider name (SC-010, Principle II)
- [X] T083 [P] Write `backend/tests/contract/test_no_secret_leak.py` — no credential value appears in any response body, header, or error message (FR-039, SC-011)
- [X] T084 [P] Write `backend/tests/unit/test_cancellation.py` — abandoning the stream stops provider consumption promptly (PC-11)
- [X] T084a [P] Write `backend/tests/contract/test_no_text_logging.py` — capture all log output during a synthesis and assert neither the submitted Arabic text nor any audio bytes appear in it (FR-040, Principle VII). *Added by `/speckit-analyze` finding E1: FR-040 is a constitution MUST that had zero task coverage.*
- [X] T085 Add request-timeout enforcement verification across every adapter (FR-032, PC-07)
- [X] T086 [P] Write `docs/TTS_EVALUATION.md` — Azure, ElevenLabs and Google compared on all 14 criteria from FR-043, with the five recommendations of FR-044, every claim cited (Principle V)
- [X] T087 [P] Write `docs/ARABIC_TEST_CASES.md` — the full sample set with expected behaviour per case (FR-038, FR-038a)
- [X] T088 [P] Write `docs/PRONUNCIATION.md` — the observed defect, technique, before/after, and how to extend the dictionary (FR-019)
- [X] T089 [P] Write `docs/BENCHMARK_RESULTS.md` from actual benchmark output, stating the measuring environment (FR-037, Principle V)
- [X] T090 [P] Write `docs/PRODUCTION_ARCHITECTURE.md` — the full avatar pipeline, where latency accumulates and how to reduce it, plus barge-in, cancellation, session state, dialect detection, caching, observability, security, rate limiting, scaling, privacy (FR-046, FR-042a)
- [X] T091 Write `README.md` — exact setup and run commands, which capabilities need credentials, and known limitations (FR-047, SC-013)
- [X] T092 Run the full offline suite and confirm it passes with integration tests **skipped**, not failed (SC-015)
- [X] T093 Execute quickstart V1–V13 end to end and record the actual outcomes (Principle V, plan §Definition of Done)

---

## Coverage of the requested 16-phase outline

The requester's phase list maps onto the user-story organization above as follows.

| Requested phase | Tasks |
|---|---|
| 1 Project setup | T001–T006 |
| 2 Provider research/evaluation | Phase 0 `research.md`, `docs/PROVIDER_RESEARCH_NOTES.md`, T086 |
| 3 Python domain models | T008–T013 |
| 4 Arabic preprocessing | T032–T049 |
| 5 TTS provider adapters | T014, T016, T023–T024, T055–T058 |
| 6 Core TTS service | T026, T050, T060 |
| 7 Streaming | T028–T029 |
| 8 Minimal frontend | T031, T053, T064, T075, T080 |
| 9 Pronunciation demo | T076–T081 |
| 10 Arabic evaluation suite | T067–T068, T087 |
| 11 Benchmarking | T069–T074, T089 |
| 12 Dialect/voice routing | T018, T025, T054, T063 |
| 13 Tests | T020–T021, T029–T030, T032–T048, T052, T061–T062, T065–T069, T074, T079, T082–T084 |
| 14 Documentation | T086–T091 |
| 15 Production architecture | T090 |
| 16 Final verification | T092–T093 |

## Dependencies

```text
Phase 1 Setup
   └─> Phase 2 Foundational  (blocks everything)
          ├─> Phase 3 US1 (P1)  ── MVP
          │       └─> Phase 4 US2 (P1)   needs the synthesis path
          │              ├─> Phase 5 US3 (P2)
          │              └─> Phase 6 US4 (P2)
          │                     └─> Phase 7 US5 (P3)  needs US2 rules + US1 audio
          └─> Phase 8 Polish (after the stories it documents)
```

US3 and US6 are independent of each other and may proceed in parallel once US2 lands.
Within Phase 7, **T076 → T077 is a hard sequence**, not a preference.

## Parallel Execution Examples

- **Phase 2**: T007, T008, T012, T016 in parallel (distinct files, no shared state)
- **Phase 4**: all test tasks T032, T034, T036, T038, T040, T042, T044, T048 in parallel; each implementation follows its own test
- **Phase 8**: T086–T090 documentation in parallel (distinct files)

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1)** — Arabic text produces streaming Arabic speech.
That alone is a demonstrable product.

Increments: **+US2** makes it correct on real-world content (the largest quality jump);
**+US3** proves provider independence and dialect coverage; **+US4** makes latency claims
measured rather than asserted; **+US5** adds the persuasive before/after proof.

**Total: 93 tasks** — US1 10, US2 22, US3 12, US4 10, US5 6, Setup 6, Foundational 15,
Polish 12.

---

## Phase 9: Convergence

**Purpose**: Close test-coverage gaps found by `/speckit-converge` — real, already-working
behavior that lacked a regression test proving it. No constitution violations and no missing
functionality were found; all four items are `partial` (HIGH/HIGH/MEDIUM/LOW).

- [X] T094 Add `backend/tests/unit/test_provider_formatting.py` asserting `prosody_for_style` returns measurably distinct (rate, pitch, volume) tuples across at least 3 styles, and that NEUTRAL is the zero baseline, per SC-006 (partial)
- [X] T095 Add `backend/tests/contract/test_api_tts.py` cases for AC-08 (induced primary failure via a monkeypatched/fake provider returns `used_fallback: true` through `/api/tts`) and AC-09 (empty provider registry returns 503 and the app process keeps serving `/health`), per contracts/http-api.md (partial)
- [X] T096 Parametrize `backend/tests/unit/test_voice_router.py::test_resolve_by_dialect_family` across all 5 `Dialect` values (msa, gulf, egyptian, levantine, maghrebi), asserting each resolves to a locale in `locales_for_dialect`, per FR-025a (partial)
- [X] T097 Add a test using `FakeProvider(chunk_delay_s=...)` that exceeds a short `timeout_s` and asserts a `ProviderError(kind="timeout")` surfaces, per contracts/provider-interface.md PC-07 (partial)

---

## Phase 10: Convergence

**Purpose**: Second `/speckit-converge` pass, after Phase 9 was completed. Confirms Phase 9's
four findings are resolved (118/118 tests passing) and surfaces one further MEDIUM gap.

- [X] T098 Add `backend/tests/contract/test_api_voices.py` covering `/api/voices` (filters by provider and locale, returns 32 voices for edge), `/api/locales` (16 locales returned), per FR-023 (partial)
- [X] T099 Add `backend/tests/contract/test_api_benchmark.py` covering `/api/samples` (returns the 11-sample set) and `/api/benchmark` (runs against the fake-registered provider path, or asserts a 404 for an unknown provider id), per FR-035, FR-038 (partial)
- [X] T100 Add `backend/tests/contract/test_api_pronunciation.py` covering `/api/pronunciation/demo` (returns the recorded demo with required provenance fields) and `/api/pronunciation/demo/audio` (200 for both corrected=true/false against the generated files, 404 with actionable detail if absent), per FR-019, FR-020 (partial)
