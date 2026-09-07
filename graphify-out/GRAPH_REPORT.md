# Graph Report - tts-project  (2026-09-07)

## Corpus Check
- 24 files · ~110,416 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1001 nodes · 2314 edges · 60 communities (32 shown, 12 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- TTS API and Streaming
- Specify Python Utilities
- Dialect API
- Voice API
- React App Components
- Arabic Text Normalization
- Provider Interface
- Dates and Currencies
- Pronunciation and App Entry
- Frontend Package Dependencies
- Workflow Shell Helpers
- Benchmark API
- Provider Errors and Endpoint
- Spec-Kit Workflows
- Frontend Build Boundary
- Hugging Face Registry
- ElevenLabs Provider
- Hugging Face Provider
- TypeScript Configuration
- Audio Models and Fakes
- Groq Adapter Tests
- Provider Conformance
- Settings and Live Tests
- Credential Availability
- Provider Requests and Observation
- Groq Provider
- Groq Limits Tests
- TTS API Contract Tests
- Evaluation and Research
- Architecture Boundary Tests
- Secret Leak Tests
- Voice API Tests
- Benchmark API Tests
- Privacy Logging Tests
- Pronunciation Strategies
- Checklist Tooling
- Engineering Instructions
- TTS Provider Contract
- Route Helpers
- Project Metadata
- Arabic Requirements Checklist
- Requirements Quality Checklist
- HTTP API Contract
- Implementation Tasks

## God Nodes (most connected - your core abstractions)
1. `ProviderRequest` - 70 edges
2. `ProviderError` - 55 edges
3. `Settings` - 55 edges
4. `TTSProvider` - 41 edges
5. `ProviderRegistry` - 41 edges
6. `VoiceConfig` - 40 edges
7. `ProviderStatus` - 39 edges
8. `GroqProvider` - 37 edges
9. `FakeProvider` - 36 edges
10. `HuggingFaceProvider` - 36 edges

## Surprising Connections (you probably didn't know these)
- `React and TypeScript Frontend` --semantically_similar_to--> `React Typed Presentation Layer`  [INFERRED] [semantically similar]
  README.md → specs/001-arabic-tts-prototype/plan.md
- `React Production Bundle` --semantically_similar_to--> `Vite Assets in frontend/dist`  [INFERRED] [semantically similar]
  README.md → specs/001-arabic-tts-prototype/plan.md
- `Typed Frontend API Client` --semantically_similar_to--> `Typed Frontend HTTP Adapter`  [INFERRED] [semantically similar]
  README.md → specs/001-arabic-tts-prototype/plan.md
- `No Routing or Linguistic Domain Logic in Browser` --semantically_similar_to--> `Python Owns Routing Dialect Processing Validation and Fallback`  [INFERRED] [semantically similar]
  README.md → specs/001-arabic-tts-prototype/spec.md
- `_run_groq()` --uses--> `ProviderError`  [INFERRED]
  scripts/observe_dialect_tts.py → backend/app/providers/base.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Full Spec-Driven Development Core Workflow** — _claude_skills_speckit_specify_skill_speckit_specify, _claude_skills_speckit_plan_skill_speckit_plan, _claude_skills_speckit_tasks_skill_speckit_tasks, _claude_skills_speckit_implement_skill_speckit_implement, _specify_workflows_speckit_workflow_full_sdd_cycle [EXTRACTED 1.00]
- **Arabic TTS Evaluation Evidence Chain** — docs_arabic_test_cases_arabic_test_cases, docs_benchmark_results_benchmark_results, docs_dialect_evaluation_arabic_dialect_evaluation, docs_pronunciation_evaluation_dialect_scoped_partial_diacritization, docs_tts_evaluation_arabic_tts_provider_evaluation [INFERRED 0.95]

## Communities (60 total, 12 thin omitted)

### Community 0 - "TTS API and Streaming"
Cohesion: 0.05
Nodes (81): preview(), post, Synthesis endpoints: /api/tts, /api/tts/stream, /api/preview. Per…, Processed text without synthesis — no provider call, works with zero…, synthesize(), synthesize_stream(), LatencyReport, ProcessedText (+73 more)

### Community 1 - "Specify Python Utilities"
Cohesion: 0.06
Nodes (79): RuntimeError, Args, _available_docs(), _check_dir(), _check_file(), _dir_has_entries(), _json_line(), main() (+71 more)

### Community 2 - "Dialect API"
Cohesion: 0.05
Nodes (61): compare(), DialectRequest, BaseModel, field_validator, post, Dialect resolution and raw-vs-corrected comparison endpoints (US6-7). Per…, resolve(), lookup() (+53 more)

### Community 3 - "Voice API"
Cohesion: 0.06
Nodes (45): list_locales(), list_providers(), list_voices(), get, Provider, voice and locale listing endpoints (FR-023, FR-024)., Every configured provider, including ones missing credentials — never silently…, get(), DialectProfile records (FR-049). Six profiles, per spec.md's minimum: msa,… (+37 more)

### Community 4 - "React App Components"
Cohesion: 0.08
Nodes (40): App(), DialectLab(), common, CompareIcon(), EyeIcon(), IconProps, PlayIcon(), SparkIcon() (+32 more)

### Community 5 - "Arabic Text Normalization"
Cohesion: 0.06
Nodes (41): Arabic and Latin abbreviation handling (FR-012). Two distinct behaviors,…, verbalize_abbreviations(), normalize(), Arabic normalization for speech synthesis. CRITICAL (Constitution III): this…, Normalize Arabic text without changing meaning., Remove diacritics. NOT part of the pipeline. Exposed only for comparison and…, strip_tashkeel(), handle_code_switching() (+33 more)

### Community 6 - "Provider Interface"
Cohesion: 0.06
Nodes (28): ABC, ProviderStatus, Readiness. Must not raise and must not do network I/O (PC-02)., Human-readable explanation, naming the missing variable (FR-024)., Abstract base every adapter implements., Return complete audio. Raises ProviderError on failure., Yield audio chunks as they arrive. A provider declaring…, Voices this provider actually serves (PC-08). (+20 more)

### Community 7 - "Dates and Currencies"
Cohesion: 0.08
Nodes (37): _amount_words(), _currency_name(), Arabic currency verbalization (FR-011). Produces "<amount> <currency name>" in…, verbalize_currencies(), Arabic date verbalization (FR-010). Handles numeric (27/09/2026, 2026-09-27)…, Replace recognized date spans with spoken Arabic dates. Mixed-format dates…, _spoken_date(), verbalize_dates() (+29 more)

### Community 8 - "Pronunciation and App Entry"
Cohesion: 0.07
Nodes (26): get_demo(), get_demo_audio(), get, Pronunciation demo endpoints (FR-019, FR-020)., health(), FastAPI application entry point. Constitution VII: request bodies validated by…, PronunciationDemo, PronunciationRule (+18 more)

### Community 9 - "Frontend Package Dependencies"
Cohesion: 0.05
Nodes (38): dependencies, @fontsource/ibm-plex-mono, @fontsource-variable/noto-kufi-arabic, @fontsource-variable/noto-sans-arabic, react, react-dom, devDependencies, jsdom (+30 more)

### Community 10 - "Workflow Shell Helpers"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 11 - "Benchmark API"
Cohesion: 0.13
Nodes (29): benchmark(), BenchmarkRequest, list_samples(), BaseModel, get, post, Benchmark endpoints (FR-035, FR-038)., The Arabic evaluation sample set (FR-038, FR-038a). Each difficult-content… (+21 more)

### Community 12 - "Provider Errors and Endpoint"
Cohesion: 0.18
Nodes (17): ProviderError, Exception, The provider abstraction. Every vendor integration lives behind this interface.…, The only exception type a provider may raise outward (PC-06). ``message`` must…, Dedicated Hugging Face Inference Endpoint backend (research.md R12 —…, synthesize(), Hosted Hugging Face Inference API backend (research.md R12 — the default…, Call the hosted Inference API for a `dialect_tts` model. Raises ProviderError,… (+9 more)

### Community 13 - "Spec-Kit Workflows"
Cohesion: 0.09
Nodes (23): Speckit Analyze, Speckit Clarify, Speckit Constitution, Speckit Converge, Speckit Implement, Speckit Plan, Speckit Specify, Speckit Tasks (+15 more)

### Community 14 - "Frontend Build Boundary"
Cohesion: 0.09
Nodes (23): Arabic RTL Document Context, TypeScript React Module Entrypoint /src/main.tsx, React Root Mount Element, Vite Application Shell, Vite /api Proxy to FastAPI, No Routing or Linguistic Domain Logic in Browser, FastAPI Backend on Port 8000, React Production Bundle (+15 more)

### Community 15 - "Hugging Face Registry"
Cohesion: 0.18
Nodes (12): enabled_for_task(), get(), The Hugging Face Model Evaluation Matrix, as loadable data (FR-055, FR-058).…, Look up a registry entry by id. Never raises (mirrors provider.available())., HFModelConfig, Dialect and Hugging Face model-registry types (US6-7, FR-048-FR-062). Additive…, A model-registry record (FR-055, FR-058). An entry with ``license is None`` or…, Thin accessor over `data/hf_model_registry.py` (FR-055). The only module the… (+4 more)

### Community 16 - "ElevenLabs Provider"
Cohesion: 0.18
Nodes (11): ElevenLabsProvider, _patch_client(), asyncio, ElevenLabs adapter tests (US1). Real live calls are exercised in…, Force ElevenLabsProvider.stream()'s internally constructed httpx.AsyncClient…, Regression: live-discovered — the free tier rejects API calls to public…, test_402_is_distinguishable_from_401(), test_402_maps_to_payment_required_not_bad_request() (+3 more)

### Community 17 - "Hugging Face Provider"
Cohesion: 0.24
Nodes (13): HuggingFaceProvider, _voice_for_model(), asyncio, Hugging Face provider adapter tests (FR-060, T133). Mocks `InferenceClient`…, _settings(), test_available_reflects_settings(), test_capabilities_is_pure_and_stable(), test_get_voices_only_includes_enabled_registry_entries() (+5 more)

### Community 18 - "TypeScript Configuration"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+10 more)

### Community 19 - "Audio Models and Fakes"
Cohesion: 0.16
Nodes (8): AudioFormat, FakeProvider, Deterministic test double (research R9). Gives the offline suite precise…, fake_provider(), Shared pytest fixtures. Fully offline — no provider credentials required., asyncio, Abandoning the stream stops provider consumption promptly (PC-11)., test_breaking_out_of_stream_stops_consumption()

### Community 20 - "Groq Adapter Tests"
Cohesion: 0.23
Nodes (13): _chunk_text(), _concat_wav(), Groq Orpheus Arabic (Saudi dialect) adapter (research R1). Credential-gated.…, Split `text` into <=`limit`-char segments, never mid-word. Splits at sentence…, Merge sequential WAV files into one valid WAV (matching parameters)., _make_wav(), Groq adapter: 200-char chunking and WAV stitching (research R1). These are new…, test_chunk_text_empty_input_returns_one_empty_segment() (+5 more)

### Community 21 - "Provider Conformance"
Cohesion: 0.22
Nodes (13): asyncio, parametrize, Provider conformance suite (contracts/provider-interface.md PC-01..PC-12). Runs…, Scope note (Constitution V — measured, not claimed): FakeProvider does not…, test_pc01_capabilities_pure(), test_pc02_available_never_raises(), test_pc03_streaming_providers_override_stream(), test_pc04_pc05_fake_stream_yields_valid_chunks() (+5 more)

### Community 22 - "Settings and Live Tests"
Cohesion: 0.27
Nodes (11): get_settings(), Application settings. Secrets are read from the environment only and are never…, asyncio, Live provider tests (research R9). Skipped when credentials are absent — never…, Edge needs no credentials, but this still hits the live network endpoint, so it…, Quickstart V15's automated counterpart (T159/T160): the one enabled dialect_tts…, test_edge_live_synthesis_produces_audio(), test_elevenlabs_live_synthesis_when_configured() (+3 more)

### Community 23 - "Credential Availability"
Cohesion: 0.21
Nodes (6): Settings, Missing credentials -> reported unavailable, never an exception (FR-024)., test_elevenlabs_missing_credentials_reports_status_not_exception(), test_groq_missing_credentials_reports_status_not_exception(), test_groq_with_credentials_reports_available(), BaseSettings

### Community 24 - "Provider Requests and Observation"
Cohesion: 0.29
Nodes (8): ProviderRequest, BaseModel, Normalised synthesis request handed to an adapter. Carries no vendor-specific…, main(), Generate audio for the Egyptian dialect sample sentences through every…, _run_edge_locale(), _run_groq(), _run_huggingface()

### Community 25 - "Groq Provider"
Cohesion: 0.22
Nodes (4): AsyncClient, GroqProvider, test_available_reflects_settings(), test_capabilities_report_saudi_dialect_not_streaming()

### Community 26 - "Groq Limits Tests"
Cohesion: 0.24
Nodes (10): client(), _noop_coro(), asyncio, Regression: live-discovered 10 req/min limit on this model (not in the vendor…, test_get_voices_are_gulf_dialect_and_scoped_to_provider(), test_rate_limit_retries_once_then_succeeds(), test_rate_limit_twice_raises_retryable_error(), test_stream_without_credentials_raises_auth_error() (+2 more)

### Community 27 - "TTS API Contract Tests"
Cohesion: 0.20
Nodes (5): API contract tests (contracts/http-api.md AC-01, AC-02, AC-10)., A primary failure that resolves via fallback must surface used_fallback=true…, Total provider unavailability is an actionable 503, and the process keeps…, test_ac08_fallback_reported_through_http_api(), test_ac09_no_provider_available_returns_503_service_stays_up()

### Community 28 - "Evaluation and Research"
Cohesion: 0.25
Nodes (8): Arabic Test Cases, Benchmark Results, Arabic Dialect Evaluation, Hugging Face Model Evaluation Matrix, Real-Time Arabic Conversational Avatar Pipeline, Arabic TTS Provider Evaluation, Voice Catalog, Phase 0 Arabic TTS Research

### Community 29 - "Architecture Boundary Tests"
Cohesion: 0.33
Nodes (6): _imports_in(), Path, No provider SDK imported outside providers/ (SC-010, Constitution II)., Services/text_processing must not contain an equality COMPARISON against a…, test_no_domain_module_branches_on_provider_name(), test_no_provider_sdk_outside_providers_package()

### Community 30 - "Secret Leak Tests"
Cohesion: 0.29
Nodes (5): No credential value appears in any response, header, or error (FR-039, SC-011)., Names-only for anything credential-shaped (FR-039); a non-secret default like a…, test_elevenlabs_unavailable_reason_never_contains_key_value(), test_env_example_has_no_credential_values(), test_unavailable_reason_never_contains_key_value()

### Community 34 - "Pronunciation Strategies"
Cohesion: 0.67
Nodes (3): Dialect-Scoped Partial Diacritization, Targeted Whole-Word Diacritization, Provider-Independent Orthographic Rewriting

## Knowledge Gaps
- **91 isolated node(s):** `arabic-tts-prototype`, `common.sh script`, `Speckit Tasks to Issues`, `Speckit Checklist`, `Constitution Template` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 364 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProviderRequest` connect `Provider Requests and Observation` to `TTS API and Streaming`, `Dialect API`, `Voice API`, `Provider Interface`, `Benchmark API`, `Provider Errors and Endpoint`, `ElevenLabs Provider`, `Hugging Face Provider`, `Audio Models and Fakes`, `Groq Adapter Tests`, `Provider Conformance`, `Settings and Live Tests`, `Groq Provider`, `Groq Limits Tests`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `ProviderRegistry` connect `TTS API and Streaming` to `Dialect API`, `Voice API`, `Provider Interface`, `Benchmark API`, `Credential Availability`, `TTS API Contract Tests`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `ProviderError` connect `Provider Errors and Endpoint` to `TTS API and Streaming`, `Dialect API`, `Voice API`, `Provider Interface`, `Hugging Face Registry`, `ElevenLabs Provider`, `Hugging Face Provider`, `Audio Models and Fakes`, `Groq Adapter Tests`, `Provider Conformance`, `Settings and Live Tests`, `Provider Requests and Observation`, `Groq Provider`, `Groq Limits Tests`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `ProviderRequest` (e.g. with `AudioFormat` and `EmotionStyle`) actually correct?**
  _`ProviderRequest` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ProviderError` (e.g. with `synthesize()` and `synthesize_stream()`) actually correct?**
  _`ProviderError` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Settings` (e.g. with `ElevenLabsProvider` and `GroqProvider`) actually correct?**
  _`Settings` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `TTSProvider` (e.g. with `Capabilities` and `ProviderStatus`) actually correct?**
  _`TTSProvider` has 12 INFERRED edges - model-reasoned connections that need verification._