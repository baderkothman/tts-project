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
- [X] T003 [P] Create `.env.example` listing `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `TTS_DEFAULT_PROVIDER`, `TTS_FALLBACK_PROVIDER`, `TTS_REQUEST_TIMEOUT_S`, `TTS_MAX_INPUT_CHARS` — names only, no values (FR-039)
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
- [X] T055 [US3] Implement `backend/app/providers/groq.py` — Groq Orpheus Arabic (Saudi dialect) REST adapter with internal 200-char chunking + WAV stitching, credential-gated `available()` (R1)
- [X] T056 [US3] Declare Groq `Capabilities`: ssml false, phoneme false, streaming false, **native_emotions false** (no vocal-direction tags documented for the Arabic model), `dialect=GULF` for its voices (R1, R2)
- [X] T057 [US3] Implement `backend/app/providers/elevenlabs.py` — ElevenLabs adapter with SSE streaming, voice-settings style mapping, credential-gated `available()` (R1, R3)
- [X] T058 [US3] Declare ElevenLabs `Capabilities` with an **empty dialect set** and phoneme false for Arabic, documenting that phoneme tags are English-only (R2, R4, FR-027)
- [X] T059 [US3] Implement style→prosody mapping for Edge (Groq accepts no prosody control; ElevenLabs uses voice-settings instead — R3), setting `emotion_native=False` when approximated (FR-028)
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
- [X] T086 [P] Write `docs/TTS_EVALUATION.md` — Groq, ElevenLabs, OpenAI, Gemini, Hugging Face and Google Cloud compared on all 14 criteria from FR-043, with the five recommendations of FR-044, every claim cited, Azure noted only as excluded-by-mandate (Principle V)
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

---

## Phase 11: Remediation — Azure exclusion mandate

**Purpose**: The project brief's explicit constraint — "Do not use Microsoft Azure Speech
anywhere in this project" — was violated during Phases 1–10: `azure.py` was implemented and
wired into the registry, tests, and every planning document. This phase records the
correction. Not produced by `/speckit-converge` (no gap in spec/plan/tasks coverage — the
spec itself incorrectly documented Azure); found instead by re-reading the original project
brief in full. Also closes two Deliverables from the brief that were never tasked at all.

- [X] T101 Remove `backend/app/providers/azure.py` and every Azure reference across `config.py`, `registry.py`, `data/voices.py`, `edge.py`, `provider_formatting.py`, tests, `.env.example`, `README.md`, and all Spec Kit artifacts (contradicts: hard project constraint)
- [X] T102 Implement `backend/app/providers/groq.py` — Groq Orpheus Arabic (Saudi dialect) adapter, chosen after real research (WebSearch/WebFetch, fetched 2026-09-07) showed it is the only one of OpenAI/Gemini/Groq/Hugging Face with a genuinely dialect-trained (non-MSA) Arabic voice; handles the API's 200-char-per-call limit via word-boundary-safe chunking and `wave`-module WAV stitching, covered by `backend/tests/unit/test_groq_provider.py` (missing, per brief §Preferred Providers)
- [X] T103 [P] Write `docs/DIALECT_EVALUATION.md` — dialect-specific sample sentences (Levantine, Gulf/Saudi) evaluated per provider/voice on accent authenticity, MSA-drift, and the Edge-vs-Groq MSA-trained-vs-dialect-trained distinction (missing, per brief §Deliverables)
- [X] T104 [P] Write `docs/VOICE_CATALOG.md` — the full voice tree (provider → dialect → gender → voice), matching the brief's §Critical Requirement — More Voices structure (missing, per brief §Deliverables)
- [X] T105 Re-run the full offline suite and confirm no Azure reference and no regression (contradicts, verification)

---

## Phase 12: Remediation — real credentials live-testing

**Purpose**: The user configured real `GROQ_API_KEY` and `ELEVENLABS_API_KEY` values and
asked for live verification. Live testing found three real, vendor-undocumented issues (two
in Groq, fixed; one in ElevenLabs, an account-tier restriction outside code's control) and
one process gap (a known, external restriction surfacing as a raw `FAILED` test instead of
a clear skip, same as the missing-credentials case already handles).

- [X] T106 Fix `backend/app/data/voices.py` — Groq's live API rejects the capitalized voice names its own docs page shows; `provider_voice_id` lowercased (missing, live-discovered)
- [X] T107 Add bounded, `Retry-After`-honoring retry to `backend/app/providers/groq.py` for the live-discovered 10 req/min limit (not in vendor docs), covered by `test_rate_limit_retries_once_then_succeeds` / `test_rate_limit_twice_raises_retryable_error` (missing, live-discovered)
- [X] T108 Fix `backend/app/services/voice_router.py` — dialect resolution used a locale-string lookup (`locales_for_dialect`) scoped to Edge's locale table, which silently failed for Groq (same `ar-SA` locale, different `dialect`); now matches each voice's own `dialect` field directly, covered by `test_dialect_resolution_keys_on_voice_dialect_not_locale_string` (contradicts: routing must use capability/voice data, not a provider-specific table, per Constitution II)
- [X] T109 Run real benchmarks against live Groq; document the actual numbers, the rate-limit-driven TTFA climb, and the 3/11 sample failures honestly in `docs/BENCHMARK_RESULTS.md`, `docs/TTS_EVALUATION.md` (partial: previously "not measured" placeholders)
- [X] T110 Add `"payment_required"` to `ErrorKind` (`backend/app/providers/base.py`) and detect HTTP 402 explicitly in `backend/app/providers/elevenlabs.py`, distinct from `auth`/`bad_request` — a valid key an account plan still can't use for a given voice is a different, actionable condition; covered by `backend/tests/unit/test_elevenlabs_provider.py`; contract updated in `contracts/provider-interface.md` (missing: contract had no vocabulary for this real failure mode)
- [X] T111 Update `test_elevenlabs_live_synthesis_when_configured` to skip (with the exact reason) on `ProviderError(kind="payment_required")` rather than fail — matching the existing "skip what genuinely can't run here, fail what's actually broken" principle already applied to missing credentials (research R9); any other `ProviderError` kind still fails the test (partial: the skip policy existed for missing credentials but not for a configured-yet-restricted account)

---

## Phase 13: Remediation — ElevenLabs fully resolved live

**Purpose**: The user asked to actually fix the ElevenLabs 402 (Phase 12 only made it fail
gracefully). Diagnosed and resolved with live evidence at each step, not assumption.

- [X] T112 Diagnose the account restriction precisely: `GET /v1/voices` with the configured key returned 401 `"missing the permission voices_read"` — the key was valid but scoped without the permission needed to inspect the account's own voice library (missing, live-discovered)
- [X] T113 User granted `voices_read` on the ElevenLabs dashboard; re-queried `GET /v1/voices` live and confirmed it now returns the account's ~20 default premade voices (verification)
- [X] T114 Root-cause the original 402: confirmed live that "Rachel" (`21m00Tcm4TlvDq8ikWAM`) is a public Voice-Library voice absent from the account's own library, while "Adam" (`pNInz6obpgDQGcFmaJgB`) was already present and worked — the free tier restriction is per-voice (library vs. account), not a blanket ElevenLabs-API restriction (missing, live-discovered)
- [X] T115 Selected "Sarah" (`EXAVITQu4vr4xnSDxMaL`) as Rachel's replacement from the account's own voice list; confirmed live with a real Arabic-text synthesis call (200, real audio bytes) *before* adopting it in `backend/app/data/voices.py` (Constitution V — verify before committing a claim)
- [X] T116 Updated `ELEVENLABS_VOICES` in `data/voices.py` (Rachel → Sarah), `docs/VOICE_CATALOG.md`, `docs/TTS_EVALUATION.md`, `docs/BENCHMARK_RESULTS.md`, `README.md`, `.env.example` (added the `voices_read` permission note to prevent the same debugging cycle for future setup) (partial: catalogue and docs referenced the now-blocked voice)
- [X] T117 Ran a real ElevenLabs benchmark (`benchmarks/elevenlabs.json`, run `573aa958`): 33/33 calls succeeded, genuine SSE streaming confirmed live (T4 before T7), 494–864ms TTFA — the lowest of any integrated provider; documented honestly in `docs/BENCHMARK_RESULTS.md` and `docs/TTS_EVALUATION.md`'s recommendations (partial: previously undocumented pending resolution)
- [X] T118 Full suite re-run: `test_elevenlabs_live_synthesis_when_configured` now passes for real (no longer needs to skip) — 147 passed, 0 skipped, 0 failed (verification)

---

## Phase 14: Hugging Face Dialect and Pronunciation Layer (User Stories 6–7)

**Purpose**: Implement the strategy pivot from `/speckit-specify` (spec.md US6-7,
FR-048–FR-062) — Hugging Face as the primary experimentation layer for dialect
authenticity and pronunciation, evaluated by evidence (research.md R10-R14) against the
existing Edge/Groq/ElevenLabs stack, never assumed better. Not a `/speckit-converge`
finding — a new feature phase from an explicit strategy-change request.

**Goal**: A dialect resolves honestly (user choice or a text classifier, never invented
precision), a raw-vs-corrected comparison works for arbitrary text, and at least one real
architecture comparison per dialect is recorded with listening scores, not claimed.

**Independent Test (US6)**: Submit the Egyptian conversational sample; confirm the
Egyptian-dialect-specific HF TTS candidate (if it clears listening verification) or the
best-scoring alternative is named as the recommendation, with its score, not merely run.

**Independent Test (US7)**: Submit arbitrary Arabic text via `POST /api/dialect/compare`;
confirm two independently playable renderings and an itemized changes list.

### Setup & Foundational — model registry and data (blocking prerequisite for US6/US7)

- [X] T119 [P] Add `huggingface_hub` as an unconditional dependency and `torch`+`transformers` behind an optional `huggingface-local` extra in `pyproject.toml` (research.md R10/R12)
- [X] T120 [P] Add `HF_TOKEN` (optional, commented) to `.env.example`, following the existing Groq/ElevenLabs credential-gated pattern (FR-039)
- [X] T121 Implement `backend/app/data/hf_model_registry.py` — `HFModelConfig` records for exactly the four candidates research.md R11 cleared for use (`IbrahimAmin/marbertv2-arabic-written-dialect-classifier`, `Abdou/arabic-tashkeel-flan-t5-small`, `charsiu/g2p_multilingual_byT5_tiny_16_layers_100`, `oddadmix/chatterbox-egyptian-v0`), each with `license`, `source_url`, `dialects`, `local_supported`/`remote_supported` populated from R11; every other R11 candidate present with `enabled=False` and a `notes`-equivalent reason (unverified license/dialect claim, non-hub distribution, or NC license) (FR-055, FR-058)
- [X] T122 [P] Implement `HFModelConfig`, `DialectProfile`, `PronunciationDictionaryEntry`, `DialectDetectionResult` in `backend/app/models/dialect.py` per data-model.md
- [X] T123 [P] Write `backend/tests/unit/test_hf_model_registry.py` — no `enabled=True` entry has `license=None`; `get(id)` returns `None` (never raises) for an unknown or disabled id (FR-058)
- [X] T124 Implement `backend/app/data/dialect_profiles.py` — `DialectProfile` records for `msa`, `levantine`, `lebanese`, `gulf`, `saudi`, `egyptian`; each `dialect_family` mapped to the existing `Dialect` enum; `preferred_tts_models` referencing T121 registry ids only where R11 cleared one, `fallback_tts_models` referencing existing Edge/Groq/ElevenLabs voice ids otherwise (FR-049)
- [X] T125 [P] Write `backend/tests/unit/test_dialect_profiles.py` — every profile's `dialect_family` is a valid `Dialect` value; no `normalization_rules` entry rewrites dialect vocabulary toward MSA (FR-050)
- [X] T126 Implement `backend/app/data/pronunciation_dictionary.py` — `PronunciationDictionaryEntry` records for Arabic/Lebanese/Saudi personal names, place names, organization/product names, technical vocabulary, English loanwords, acronyms (FR-052)
- [X] T127 [P] Write `backend/tests/unit/test_pronunciation_dictionary.py` — token lookup, alias resolution, and a dialect-scoped entry taking precedence over an unscoped entry for the same token (edge case)

**Checkpoint**: Registry and dialect data exist; nothing downloaded yet (FR-058 still holds — these are data records, not model fetches).

### Hugging Face provider adapter (FR-060 — behind the existing `TTSProvider` interface)

- [X] T128 [P] Implement `backend/app/providers/huggingface/models.py` — request/response/config dataclasses for this package
- [X] T129 Implement `backend/app/providers/huggingface/inference_api.py` — hosted Inference API backend via `huggingface_hub`; maps cold start/rate limit to `ProviderError(kind="timeout"/"rate_limit")`, missing `HF_TOKEN` to `unavailable` (FR-056, FR-057, contracts/provider-interface.md)
- [X] T130 Implement `backend/app/providers/huggingface/local.py` — MPS/CPU backend; refuses to load any `HFModelConfig` not marked `local_supported`, enforcing R10's hardware ceiling in code, not only in registry data (FR-056)
- [X] T131 [P] Implement `backend/app/providers/huggingface/endpoint.py` — dedicated Inference Endpoint backend stub; raises `ProviderError(kind="unavailable")` with an actionable message until a user supplies an endpoint URL (FR-056 — documented, not required)
- [X] T132 Implement `backend/app/providers/huggingface/provider.py` — the `TTSProvider`-conformant adapter selecting a backend per resolved `HFModelConfig`; registered in `providers/registry.py` alongside Edge/Groq/ElevenLabs (FR-060)
- [X] T133 [P] Write `backend/tests/unit/test_huggingface_provider.py` — runs the existing PC-01…PC-12 conformance suite (T021) against this adapter using `httpx.MockTransport`; no live calls (FR-060)

**Checkpoint**: A fourth provider exists, conforms to the same contract, and is fully testable offline.

### Hugging Face linguistic-processing services (FR-060 — separate from TTS, not registered as a provider)

- [X] T134 [P] Implement `backend/app/text_processing/huggingface/model_registry.py` — thin accessor over T121; the only module other HF services import from (FR-055)
- [X] T135 Implement `backend/app/text_processing/huggingface/dialect_classifier.py` — calls the text dialect classifier (R13) via the T129 backend on typed Arabic text; degrades to an unavailable result, never raises, on any HF failure (FR-048, FR-057)
- [X] T136 [P] Write `backend/tests/unit/test_dialect_classifier.py` — mocked HTTP; an unavailable HF endpoint yields a degraded result, not an exception (FR-057)
- [X] T137 [P] Implement `backend/app/text_processing/huggingface/diacritizer.py` — calls the T121 diacritization model via the hosted Inference API backend (FR-052, FR-053)
- [X] T138 [P] Implement `backend/app/text_processing/huggingface/g2p.py` — calls the T121 G2P model, feeding `PronunciationDictionaryEntry.phonemes` (FR-052)
- [X] T139 Implement `backend/app/text_processing/huggingface/pronunciation_model.py` — combines T126 dictionary lookup with T137/T138 output, dialect-scoped (FR-052)

**Checkpoint**: Text-in dialect detection and pronunciation processing work end to end, offline-testable via mocks.

### User Story 6 — Hear a Dialect That Actually Sounds Like That Dialect (Priority: P2)

- [X] T140 [US6] Implement `backend/app/services/dialect_service.py::resolve()` — user selection always wins; the classifier still runs when a selection is present (for transparency, per FR-051) or runs as the primary source when none is given; returns a `DialectDetectionResult` with `mapped_from_family` set correctly (FR-048, FR-051, plan.md Design Decision 7)
- [X] T141 [P] [US6] Write `backend/tests/unit/test_dialect_service.py` — `test_user_selection_overrides_classifier`, `test_classifier_used_when_no_selection`, `test_mapped_from_family_when_classifier_coarser` (AC-11, AC-12)
- [X] T142 [US6] Implement `POST /api/dialect/resolve` in `backend/app/api/dialect.py` (contracts/http-api.md)
- [X] T143 [P] [US6] Write `backend/tests/contract/test_api_dialect.py::test_resolve_*` covering AC-11, AC-12, AC-13
- [X] T144 [US6] Create `scripts/observe_dialect_tts.py` (mirrors `scripts/observe_pronunciation.py`'s pattern, Principle V) and **run it**: synthesize the Egyptian sample sentences through `oddadmix/chatterbox-egyptian-v0`, listen, and record whether it actually produces recognizably Egyptian speech before wiring it into `DialectProfile.preferred_tts_models` for `egyptian` (FR-054, FR-061)
- [~] T145 [US6] **Partially done, now with a confirmed root cause**: existing-TTS
  baselines (Edge `ar-EG`, and for Gulf/Saudi Edge `ar-SA` + live Groq) were run and real
  audio recorded. The HF-native leg was retried after a real `HF_TOKEN` was configured and
  correctly permissioned (`inference.serverless.write`, after fixing an initial 403 —
  T112-style permission gap) — `oddadmix/chatterbox-egyptian-v0` is **confirmed live**
  (400, "Model not supported by provider hf-inference"; model metadata shows
  `inference: null`) to not be deployed on any Hugging Face Inference Provider. This is a
  genuine platform constraint, not a missing token or a code defect — the FR-061 /5
  listening scores still cannot be produced because no audio exists to score, but the
  *reason* is now definitively established rather than "blocked, untested." Recorded in
  `docs/DIALECT_EVALUATION.md`'s "Update (2026-09-07...)" subsection. `preferred_tts_models`
  correctly remains empty — using this model in production would need a paid Dedicated
  Inference Endpoint or local execution (FR-054, SC-016, Constitution V)
- [X] T146 [US6] Repeat T145's methodology for Lebanese/Levantine and Saudi/Gulf using Edge and Groq as the baseline architectures (no dialect-specific HF TTS candidate cleared R11 for these two yet) plus Hugging Face preprocessing; record this state honestly as "HF preprocessing evaluated, no verified HF-native candidate" rather than omitting the dialects (FR-054, SC-016, Constitution V)
- [X] T147 [US6] Add the "why this dialect" display to the frontend dialect panel — resolved dialect, source, classifier label and confidence when applicable (Story 6, Scenarios 3-4)

**Checkpoint**: Every dialect in scope has a recorded, evidence-based architecture recommendation — including the honest "no HF-native option yet" cases.

### User Story 7 — Compare Raw vs. Hugging-Face-Corrected Speech for Any Text (Priority: P2)

- [X] T148 [US7] Implement `dialect_service.compare()` assembling `DialectComparisonResult` — reuses `text_processing/pipeline.py` for the corrected path and produces both audio references (FR-053, plan.md Design Decision 8)
- [~] T149 [US7] **Partially done**: `POST /api/dialect/compare` implemented, tested, and live-verified (quickstart V14). The `GET /api/pronunciation/demo` refactor onto the same assembly (Design Decision 8) was **deliberately deferred** — Story 5's demo endpoint was already correct and covered by `test_api_pronunciation.py` (T100), and the refactor's risk of destabilizing tested, working code outweighed the benefit of eliminating a small amount of duplicated comparison-assembly logic at this pass; disclosed in README.md's Known limitations rather than silently dropped
- [X] T150 [P] [US7] Write `backend/tests/contract/test_api_dialect.py::test_compare_*` covering AC-14 and the no-correction-applied case (Story 7, Scenario 3)
- [X] T151 [US7] Add the raw-vs-corrected comparison panel to `frontend/index.html` — accepts arbitrary user text (not only the fixed demo), shows resolved dialect/source/confidence, the changes list, and both audio players
- [X] T152 [P] [US7] Write `backend/tests/unit/test_dialect_comparison.py` — text with no applicable correction returns `changes: []` and identical raw/corrected audio content, never a fabricated difference (Story 7, Scenario 3)

**Checkpoint**: US6 and US7 complete — the raw/corrected comparison generalizes beyond the fixed Story 5 demo, and Story 5 now runs through the same code path.

### Polish, evaluation and documentation

- [X] T153 [P] Write `docs/HF_MODEL_RESEARCH.md` from research.md R10-R14 — the full Model Evaluation Matrix with sources, which models were actually wired in (T121) vs. recorded as leads/rejected and why (FR-058)
- [X] T154 [P] Write `docs/PRONUNCIATION_EVALUATION.md` — raw vs. partially-diacritized vs. fully-diacritized comparison (per the brief's explicit "do not blindly add full tashkeel" instruction), backed by real generated audio from T137
- [X] T155 Update `docs/DIALECT_EVALUATION.md` with T145/T146's results and explicit FR-062 answers per dialect (Lebanese/Levantine, Saudi/Gulf, Egyptian, MSA): did HF measurably improve dialect authenticity, did it measurably improve pronunciation, which model/architecture won, should HF generate final audio or only preprocess for an existing provider — each traceable to a T145/T146 score
- [X] T156 [P] Update `docs/VOICE_CATALOG.md` — the `DialectProfile` table showing, per dialect, confirmed-HF-native / HF-preprocessing-only / no-live-HF-option status
- [X] T157 Update `docs/PRODUCTION_ARCHITECTURE.md` — where the HF linguistic-processing layer sits in the documented avatar pipeline (mic → VAD → streaming STT → dialect detection → LLM → HF pronunciation layer → voice router → streaming TTS → audio), per FR-046 and the spec's architecture diagram
- [X] T158 Update `README.md` — `HF_TOKEN` setup, which capabilities are credential-gated vs. work offline, updated test count (FR-047)
- [X] T159 Run the full offline suite and confirm it passes with HF integration tests reported as **skipped**, not failed, when `HF_TOKEN` is absent (mirrors SC-015 for this layer)
- [X] T160 Execute quickstart V14–V15 end to end and record the actual outcomes, including which parts required `HF_TOKEN` and which worked credential-free (Principle V)

**Total for Phase 14: 42 tasks** (T119–T160) — Setup/Foundational 9, HF provider 6, HF
linguistic services 6, US6 8, US7 5, Polish 8.

## Dependencies (Phase 14)

```text
Phase 13 (existing suite, 147 passed) — must still pass unchanged
   └─> T119-T127 Setup/Foundational (registry + dialect data — no model downloaded yet)
          ├─> T128-T133 HF provider adapter
          ├─> T134-T139 HF linguistic-processing services
          │      └─> T140-T147 US6 (needs dialect_classifier + pronunciation_model)
          │      └─> T148-T152 US7 (needs pipeline integration + US6's dialect_service.resolve())
          └─> T153-T160 Polish (needs US6+US7 results to document honestly)
```

T144 → T145 is a hard sequence, the same discipline Phase 7's T076 → T077 already
established: a dialect-authenticity claim cannot be recorded before the audio that would
support it has actually been generated and listened to.

---

## Phase 15: Remediation — closing /speckit-analyze findings C1 and C2

**Purpose**: `/speckit-analyze`, run against the appended Phase 14 task list before
implementation, found two HIGH task-coverage gaps. The user chose to close them
opportunistically during implementation rather than adding tracked pre-tasks first
("Proceed to implement as-is, fix gaps during implementation"); this phase records what was
actually done so the gaps are not left silently closed.

- [X] T161 Close analyze finding C1 (FR-059: HF voice gender defaults): `providers/huggingface/provider.py::_voice_for_model` sets `gender="unknown"` explicitly on every Hugging Face voice, since no cleared `dialect_tts` candidate documents speaker/gender metadata (research.md R11) — asserted by `test_huggingface_provider.py::test_voices_have_honest_unknown_gender` (missing → closed)
- [X] T162 Close analyze finding C2 (FR-057/SC-019: end-to-end fallback when a dialect's HF component is unavailable): `services/dialect_service.py::select_voice_for_dialect()` prefers an available Hugging Face model, then falls through to the resolved `DialectProfile.fallback_tts_models` against the first *available* existing provider, then the registry's own default — never raising for a dialect with no HF component, mirroring `tts_service._try_fallback`'s existing pattern; asserted by `test_dialect_service.py::test_select_voice_falls_back_to_existing_provider_when_hf_unavailable` and `::test_select_voice_unknown_dialect_falls_back_to_msa_profile` (partial → closed)

**Verification**: full suite after Phase 14 + Phase 15: **186 passed, 2 skipped (both
`HF_TOKEN`-gated), 0 failed** — see `docs/HF_MODEL_RESEARCH.md`, `docs/DIALECT_EVALUATION.md`,
`docs/PRONUNCIATION_EVALUATION.md` for the evidence-based findings this phase's tasks
produced, and README.md's Known limitations for what remains genuinely incomplete (T145's
HF-native comparison leg, T149's demo-endpoint refactor) rather than claimed done.

---

## Phase 16: Convergence

**Purpose**: `/speckit-converge`, run after Phase 14-15 implementation, checked the built
code against spec.md/plan.md's Hugging Face requirements (US6-7, FR-048–FR-062). Two
`partial`/`missing` gaps found (both MEDIUM); everything else — dialect resolution honesty,
the pronunciation dictionary, the live comparison endpoint, the model registry gate,
provider-interface separation, and the FR-062 evaluation answers — checks out against real,
tested, largely live-verified code.

- [ ] T163 Wire local MPS/CPU execution for at least one small Hugging Face linguistic-processing model (the text dialect classifier is the best candidate: 200M params, `local_supported=True` in the registry) so FR-056's "at least two execution modes" claim is backed by working code — currently `providers/huggingface/local.py` and every `text_processing/huggingface/*.py` module call only the hosted Inference API, with no functional local path for any capability (partial, FR-056)
- [ ] T164 Add spec.md's Story 6 Lebanese/Gulf/Egyptian conversational sample sentences (the same 12 sentences `scripts/observe_dialect_tts.py` already uses live) as `ArabicSample` records in `backend/app/data/samples.py`, `category="dialect"`, with dialect-appropriate `expected_behavior` per FR-038a's per-sample assertion pattern — currently exposed nowhere outside the standalone script, so not queryable via `GET /api/samples`, not benchmarkable, and not covered by `test_samples.py` (missing, FR-038/US6)

---

## Phase 17: Remediation — HF_TOKEN live-verification (real platform findings, not credential-gated placeholders)

**Purpose**: The user configured a real `HF_TOKEN` and asked to complete the live
verification T144/T145 had left honestly blocked. Diagnosed with the same live-probe
methodology already proven on Groq/ElevenLabs (raw `httpx`/SDK calls before deciding a
fix) rather than guessed at.

- [X] T165 Diagnose the initial 403 precisely: `GET /api/whoami-v2` showed the configured token was `fineGrained` with only `repo.content.read` — missing `inference.serverless.write`, the permission needed to call any model through Hugging Face's Inference Providers system (same class of gap as the earlier ElevenLabs `voices_read` fix, T112) (missing, live-discovered)
- [X] T166 User granted `inference.serverless.write` on the token; re-queried `GET /api/whoami-v2` live and confirmed the permission now appears (verification)
- [X] T167 Fix a real, independent bug found while diagnosing: `text_processing/huggingface/{dialect_classifier,diacritizer,g2p}.py`'s raw `httpx` calls were pointed at `api-inference.huggingface.co`, Hugging Face's legacy free-tier hostname — confirmed via direct `host`/`nslookup` that it no longer resolves in DNS at all. Fixed to `router.huggingface.co/hf-inference/models`, the current Inference Providers gateway (contradicts: FR-057's graceful-degradation path was masking a genuine dead-endpoint bug behind a generic "unreachable" message)
- [X] T168 Root-cause the still-failing calls after the URL and permission fixes: `providers/huggingface/inference_api.py` used `InferenceClient`'s default "auto" provider selection, which raises a bare, unmappable `StopIteration` when no third-party provider serves a niche model — fixed to request `provider="hf-inference"` explicitly, which returns a real, mappable HTTP error instead (missing: the "auto" default was silently swallowing the actual vendor error)
- [X] T169 With the URL and provider-selection fixes in place, confirmed live and definitively: `oddadmix/chatterbox-egyptian-v0` returns `400` "Model not supported by provider hf-inference" (model metadata: `inference: null`); `IbrahimAmin/marbertv2-arabic-written-dialect-classifier` returns `410 Gone` "deprecated and no longer supported by provider hf-inference" — both are genuine Hugging Face platform constraints (the model isn't deployed on any Inference Provider), not token, permission, or code defects (missing, live-discovered)
- [X] T170 Updated `test_huggingface_live_synthesis_when_configured` and `test_huggingface_dialect_classifier_live_when_configured` to skip on this specific, confirmed condition (matching ElevenLabs' `payment_required` skip precedent) rather than fail raw; re-ran `scripts/observe_dialect_tts.py` live, confirming the same finding through the standalone script path (partial: the skip policy existed for missing credentials but not for a configured-yet-platform-blocked model)
- [X] T171 Updated `data/hf_model_registry.py` notes, `docs/HF_MODEL_RESEARCH.md`, `docs/DIALECT_EVALUATION.md` (full FR-062 answers rewritten from "not yet determined, no token" to "confirmed blocked by the platform, here's why and what it would actually take"), and `README.md`'s Known Limitations (partial: docs previously described a token-gated unknown, now describe a live-confirmed, specific platform constraint)

**Verification**: full suite after Phase 17: **186 passed, 2 skipped (both citing the
confirmed platform reason, not "HF_TOKEN not configured"), 0 failed**.
