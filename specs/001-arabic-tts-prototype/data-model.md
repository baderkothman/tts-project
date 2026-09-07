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
