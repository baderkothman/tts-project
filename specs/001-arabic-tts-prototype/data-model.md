# Phase 1 Data Model: Arabic Text-to-Speech Prototype

**Date**: 2026-09-07 | **Feature**: `001-arabic-tts-prototype`

All models are Pydantic v2. Validation rules trace to the functional requirements they
enforce. No model imports a provider SDK type (Constitution Principle II).

---

## Enumerations

### `Dialect`

Dialect *family*, distinct from an exact locale (FR-025a).

| Value | Meaning | Locales routed to it |
|-------|---------|----------------------|
| `msa` | Modern Standard Arabic | ar-SA |
| `gulf` | Gulf | ar-AE, ar-KW, ar-QA, ar-BH, ar-OM, ar-IQ |
| `egyptian` | Egyptian | ar-EG |
| `levantine` | Levantine | ar-LB, ar-SY, ar-JO |
| `maghrebi` | Maghrebi | ar-MA, ar-DZ, ar-TN |

`ar-LY` and `ar-YE` are catalogued as locales without a family claim, per FR-027 — asserting
a family for them would exceed what the provider documents.

### `EmotionStyle`

`neutral`, `happy`, `excited`, `sad`, `warm`, `calm`, `serious`, `conversational`.

Normalized across providers (FR-028). Each adapter maps these to whatever it actually
supports and reports whether the result was native or approximated.

### `AudioFormat`

`mp3_24khz` (default), `mp3_48khz`, `pcm_16khz`, `pcm_24khz`, `opus_24khz`.

### `ProviderStatus`

`available`, `missing_credentials`, `unreachable`.

A provider is never absent from the listing — FR-024 requires it be *reported* as
unavailable, so the user learns it exists and what would enable it.

---

## Request and Response

### `TTSRequest`

| Field | Type | Rules | Requirement |
|-------|------|-------|-------------|
| `text` | `str` | min 1 after strip, **max 5000** | FR-003, FR-042 |
| `locale` | `str \| None` | pattern `^[a-z]{2}-[A-Z]{2}$` | FR-026 |
| `dialect` | `Dialect \| None` | — | FR-025a |
| `provider` | `str \| None` | must be a registered id | FR-021 |
| `voice_id` | `str \| None` | must belong to the resolved provider | FR-026 |
| `emotion` | `EmotionStyle` | default `neutral` | FR-028 |
| `speaking_rate` | `float \| None` | 0.5–2.0 | — |
| `pitch` | `float \| None` | −20.0–20.0 (semitones) | — |
| `output_format` | `AudioFormat` | default `mp3_24khz` | FR-004 |
| `apply_preprocessing` | `bool` | default `True` | FR-020 |
| `apply_pronunciation` | `bool` | default `True` | FR-020 |
| `client_t0_ms` | `float \| None` | client clock, optional | R6 |

`apply_preprocessing` and `apply_pronunciation` are separate switches specifically so the
before/after demonstration can hold everything else constant and vary only correction
(FR-020). Whitespace-only text fails the min-length rule after stripping, which is what
makes the empty-input edge case a validation error rather than a silent empty synthesis.

### `ProcessedText`

| Field | Type | Purpose |
|-------|------|---------|
| `original` | `str` | Exactly as submitted (FR-015) |
| `processed` | `str` | Final text sent for synthesis (FR-015) |
| `stages` | `list[StageDiff]` | Per-stage record (FR-016) |
| `changed` | `bool` | Whether any stage altered the text |

### `StageDiff`

`stage_name`, `before`, `after`, `changed: bool`, `duration_ms: float`.

Recording `before`/`after` per stage is what makes the pipeline inspectable rather than a
black box, and it is the same mechanism that lets each stage be tested in isolation.

### `TTSResponse`

| Field | Type | Purpose |
|-------|------|---------|
| `audio_base64` | `str` | Non-streaming path only |
| `content_type` | `str` | e.g. `audio/mpeg` |
| `processed_text` | `ProcessedText` | FR-015 |
| `voice` | `VoiceConfig` | Which voice actually served it (FR-025) |
| `provider` | `str` | Which provider actually served it |
| `emotion_applied` | `EmotionStyle` | — |
| `emotion_native` | `bool` | `False` when prosody-approximated (R3, FR-028) |
| `used_fallback` | `bool` | FR-033 |
| `fallback_reason` | `str \| None` | Why the primary was abandoned |
| `latency` | `LatencyReport` | FR-031 |
| `audio_duration_ms` | `float \| None` | For real-time factor |

`emotion_native` and `used_fallback` exist to keep the response honest: a prosody
approximation and a substituted provider are both results the caller must be able to tell
apart from the thing they asked for.

---

## Voice and Provider

### `VoiceConfig`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Stable internal id |
| `provider` | `str` | Owning provider |
| `provider_voice_id` | `str` | Vendor's own identifier |
| `language` | `str` | `ar` |
| `locale` | `str` | e.g. `ar-EG` |
| `dialect` | `Dialect \| None` | `None` where no family is claimed (FR-027) |
| `gender` | `str` | `female` / `male` |
| `supports_streaming` | `bool` | |
| `supports_emotions` | `bool` | Native styles, not prosody approximation |
| `supports_ssml` | `bool` | |
| `latency_class` | `str \| None` | `low` / `standard` |
| `fallback_voice_id` | `str \| None` | Used on failure (FR-033) |

`dialect` being nullable is a deliberate modelling choice: it makes "no documented dialect"
representable, so ElevenLabs voices can be catalogued without inventing a claim.

### `Capabilities`

Declared per provider and consumed generically by the router (FR-023, SC-010).

`streaming: bool`, `ssml: bool`, `phoneme: bool`, `native_emotions: bool`,
`prosody_rate/pitch/volume: bool`, `locales: list[str]`, `formats: list[AudioFormat]`,
`max_chars: int`, `requires_credentials: bool`.

The router branches on **these fields only** — never on a provider name. That is the
mechanical guarantee behind Principle II, and it is what the import-boundary test verifies.

### `ProviderInfo`

`id`, `display_name`, `status: ProviderStatus`, `capabilities`, `voice_count`,
`unavailable_reason: str | None` — e.g. which environment variable is missing (FR-024).

---

## Pronunciation

### `PronunciationRule`

| Field | Type | Notes |
|-------|------|-------|
| `original` | `str` | Written form to match |
| `replacement` | `str` | Corrected orthographic or phonetic form |
| `locale` | `str \| None` | Applies everywhere when `None` |
| `provider` | `str \| None` | Provider-specific rule when set (R4) |
| `notes` | `str \| None` | Why the rule exists |
| `category` | `str` | `person`, `company`, `place`, `product`, `medical`, `banking`, `foreign`, `ambiguous` |
| `whole_word` | `bool` | Default `True` — prevents matching inside longer words |

`whole_word` defaults to `True` because Arabic attaches prefixes (و، ال، ب، ل) freely, and a
naive substring rule would corrupt unrelated words — a meaning change, which Principle III
forbids.

Rules are **data** (FR-018), so extending coverage never edits program logic.

### `PronunciationDemo`

`original_text`, `observed_pronunciation`, `desired_pronunciation`, `correction_technique`,
`corrected_text`, `provider_observed`, `voice_observed`, `explanation`.

`provider_observed` and `voice_observed` are required, not optional — FR-019 and Principle V
demand the defect be traceable to an actual synthesis, and a nullable field would let an
undocumented claim through.

---

## Latency

### `LatencyTrace` (internal)

Mutable during a request; holds `perf_counter()` marks T0–T7 (R6) and exposes
`mark(name)`. Not serialized directly.

### `LatencyReport` (response)

`preprocessing_ms` (T2−T1), `provider_ttfa_ms` (T4−T3), `backend_ttfa_ms` (T5−T1),
`total_generation_ms` (T7−T1), `audio_duration_ms`, `real_time_factor`,
`client_ttfa_ms | None` (needs client T0).

`client_ttfa_ms` is nullable because it depends on a clock the server does not own;
reporting a server-side figure under that name would be false precision (R6).

---

## Benchmarking

### `ArabicSample`

`id`, `text`, `category` (`msa`, `dialect`, `pronunciation`, `numbers`, `dates`,
`currencies`, `abbreviations`, `code_switching`, `emotion`), `locale`, `description`,
`expected_behavior: str | None` — the assertion a test can make about it (FR-038).

### `StageStats`

`min_ms`, `max_ms`, `mean_ms`, `median_ms`, `p95_ms`, `count` (FR-036).

P95 is nearest-rank, not interpolated — with five repetitions an interpolated percentile
would imply resolution the sample size does not support (R7).

### `BenchmarkResult`

One provider/voice/sample cell: `sample_id`, `provider`, `voice_id`, `repetitions`,
per-stage `StageStats`, `failures: int`, `real_time_factor` stats.

### `BenchmarkRun`

`run_id`, `started_at`, `finished_at`, `provider`, `voice_id`, `sample_set`, `repetitions`,
`warmup_discarded: bool`, `environment` (Python version, platform), `results`.

`warmup_discarded` is recorded rather than assumed, so a reader can tell steady-state
figures from cold-start ones (R7, FR-037).

---

## Relationships

```text
TTSRequest ──resolved by──> VoiceRouter ──> VoiceConfig ──belongs to──> Provider
     │                                            │
     │                                            └──> Capabilities (gates emotion/SSML/streaming)
     ▼
TextPipeline ──> ProcessedText ──> [StageDiff]
     │                    ▲
     │                    └── PronunciationRule[] (filtered by locale + provider)
     ▼
TTSService ──> Provider.stream() ──> audio chunks ──> StreamingResponse
     │
     └──> LatencyTrace ──> LatencyReport ──> TTSResponse

BenchmarkService ──> ArabicSample[] × repetitions ──> BenchmarkResult[] ──> BenchmarkRun ──> files
```

## Hugging Face Dialect and Pronunciation Layer (US6-7, FR-048–FR-062)

These entities are additive: they do not replace `Dialect` (the five-way locale-routing
family above) or `PronunciationRule` (the pattern-matched orthographic rewriter). A
`DialectProfile.id` can be **narrower** than a `Dialect` family value — e.g. `lebanese` is
a `DialectProfile` while the `Dialect` enum still only routes at `levantine` granularity
for provider-voice selection, because no integrated TTS provider (Edge/Groq/ElevenLabs)
publishes a Lebanese-specific locale (research.md R2). `DialectProfile` is where that
finer granularity becomes representable — honestly, with a confidence label — without
inventing a `Dialect` enum value no provider actually backs.

### `DialectProfile`

| Field | Type | Notes | Requirement |
|-------|------|-------|-------------|
| `id` | `str` | e.g. `lebanese`, `gulf`, `msa` — may be finer than a `Dialect` family value | FR-049 |
| `name` | `str` | Display name | FR-049 |
| `region` | `str \| None` | Free-text geographic label | FR-049 |
| `dialect_family` | `Dialect` | The `Dialect` enum value this profile maps to for provider-voice routing (e.g. `lebanese` → `levantine`) | FR-049, bridges to existing `VoiceRouter` |
| `locale` | `str \| None` | A specific provider locale this profile prefers when one exists (e.g. `ar-LB`) | FR-049 |
| `aliases` | `list[str]` | Alternate names/spellings a user or classifier might use | FR-049 |
| `normalization_rules` | `list[str]` | References into the pronunciation dictionary/rule set; MUST NOT include a rule that rewrites this dialect's vocabulary toward MSA | FR-050 |
| `pronunciation_model` | `HFModelConfig.id \| None` | Which registry entry, if any, handles pronunciation for this profile | FR-049 |
| `diacritization_model` | `HFModelConfig.id \| None` | Which registry entry, if any, diacritizes for this profile | FR-049 |
| `preferred_tts_models` | `list[HFModelConfig.id]` | Ordered; empty when no dialect-specific HF TTS model has cleared research.md's Model Evaluation Matrix yet | FR-049, FR-054 |
| `fallback_tts_models` | `list[str]` | Existing provider/voice ids (Edge/Groq/ElevenLabs) to use when no HF model applies | FR-049, FR-057 |

FR-050 is enforced at the data level, not just the code level: `normalization_rules` is
reviewed for MSA-flattening rules the same way `PronunciationRule.whole_word` prevents
substring corruption — a rule that collapses dialect vocabulary to its MSA form is a data
defect, not merely a bad runtime decision.

### `PronunciationDictionaryEntry`

| Field | Type | Notes | Requirement |
|-------|------|-------|-------------|
| `token` | `str` | Exact or aliased lookup key | FR-052 |
| `dialect` | `str \| None` | A `DialectProfile.id`; `None` applies everywhere, same nullable pattern as `PronunciationRule.locale` | FR-052 |
| `normalized` | `str \| None` | Canonical written form | FR-052 |
| `diacritized` | `str \| None` | Fully or partially diacritized form | FR-052 |
| `phonemes` | `str \| None` | G2P output, when available | FR-052 |
| `aliases` | `list[str]` | Alternate spellings that resolve to this entry | FR-052 |
| `notes` | `str \| None` | Why the entry exists | FR-052 |

Distinct from `PronunciationRule`: a dictionary entry is looked up by exact/aliased token
(names, places, products — closed-set lookup); a rule is pattern-matched (FR-017's broader
written-form-to-correction mapping). Both are consulted during pronunciation processing;
a `PronunciationDictionaryEntry` match takes precedence for the token it covers.

### `HFModelConfig`

| Field | Type | Notes | Requirement |
|-------|------|-------|-------------|
| `id` | `str` | Stable internal id (may differ from `repo_id`, e.g. when the registry pins a revision) | FR-055 |
| `repo_id` | `str` | Hugging Face Hub repository id | FR-055, FR-058 |
| `task` | `str` | `dialect_tts`, `dialect_classification`, `diacritization`, `g2p` | FR-055 |
| `dialects` | `list[str]` | `DialectProfile.id` values this model actually serves — MUST NOT list a dialect the model card does not support (Constitution V) | FR-055, FR-061 |
| `local_supported` | `bool` | Whether R10's hardware ceiling allows local execution | FR-055, FR-056 |
| `remote_supported` | `bool` | Whether it is reachable through the hosted Inference API | FR-055, FR-056 |
| `streaming` | `bool` | | FR-055 |
| `requires_gpu` | `bool` | As documented on the model card, not inferred | FR-055 |
| `approximate_vram_gb` | `float \| None` | From the model card when stated | FR-055 |
| `license` | `str \| None` | Recorded before use, per FR-058 — `None` means "unverified," which blocks use, not an implicit "permissive" | FR-058 |
| `enabled` | `bool` | Registry-level kill switch, independent of code changes | FR-055 |
| `source_url` | `str` | The model card/paper URL the above fields were verified against (research.md R11) | Constitution V |

An entry with `license: None` or `enabled: False` MUST NOT be selected by
`dialect_service` or the HF provider adapter — this is what makes FR-058's
"don't download before verifying" gate mechanical rather than a process reminder.

### `DialectDetectionResult`

| Field | Type | Notes | Requirement |
|-------|------|-------|-------------|
| `resolved_dialect` | `str` | The `DialectProfile.id` actually used | FR-048 |
| `source` | `Literal["user_selected", "classifier"]` | Which path determined it | FR-048 |
| `classifier_label` | `str \| None` | The classifier's raw output, even when overridden by user selection | FR-051 |
| `classifier_confidence` | `float \| None` | `None` when `source == "user_selected"` and the classifier did not run | FR-048, FR-051 |
| `mapped_from_family` | `bool` | `True` when `resolved_dialect` is narrower than what the classifier could actually distinguish (e.g. app prefers `lebanese`, classifier only resolves `levantine`) | FR-051 |

`classifier_label` is populated even when `source == "user_selected"` *if* the classifier
was still run for transparency (Story 6, Scenario 4) — never discarded silently.

### `DialectComparisonResult` (US7 response shape)

`original_text`, `detection: DialectDetectionResult`, `processed_text: ProcessedText`,
`changes: list[str]` (human-readable, e.g. `"pronunciation correction: token X"`,
`"diacritic added"`, `"abbreviation expanded"`), `raw_audio_ref`, `corrected_audio_ref`
(both playable, per FR-053), `architecture_used: str` (which of FR-054's four
architectures produced `corrected_audio_ref`, for traceability back to the evaluation).

---

## Validation Summary

| Rule | Enforced by | Requirement |
|------|-------------|-------------|
| Text non-empty after strip | Pydantic validator | FR-003 |
| Text ≤ 5000 chars | Pydantic `max_length` | FR-003, FR-042 |
| Locale format and support | Validator + router | FR-026 |
| Voice belongs to provider | Router check | FR-026 |
| Style supported or approximated | Capability check | FR-028 |
| Dialect claimed only where published | Voice catalogue data | FR-027 |
| Markup in text never reaches instructions | Escaping SSML builder | FR-041 |
| Credentials never serialized | No secret field on any model | FR-039 |
