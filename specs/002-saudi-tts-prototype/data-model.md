# Phase 1 Data Model: Saudi Arabic TTS Prototype

**Date**: 2026-09-07 | **Feature**: `002-saudi-tts-prototype`

All models are Pydantic v2. No model imports the Groq SDK or references a raw HTTP
response type (Constitution II) — the provider adapter translates.

---

## `Voice`

| Field | Type | Notes | Requirement |
|---|---|---|---|
| `id` | `str` | Stable internal id, e.g. `groq:abdullah` | FR-002, FR-003 |
| `name` | `str` | Display name, e.g. `Abdullah` | FR-002 |
| `provider` | `str` | Owning provider, e.g. `groq` | FR-010 |
| `gender` | `Literal["male", "female", "unknown"]` | `"unknown"` when the provider does not reliably document it — never inferred | FR-009 |
| `dialect` | `str` | Fixed `"saudi"` for every voice this feature exposes | FR-001 |
| `model` | `str` | The underlying provider model/repo id, e.g. `canopylabs/orpheus-arabic-saudi` | FR-014 (traceability) |

`gender` is a closed three-value set, not a free string, specifically so `"unknown"` is a
real, representable value rather than an empty string a caller might mistake for "not yet
loaded" (a modelling lesson carried from 001's `VoiceConfig.dialect: Dialect | None`
pattern — nullable/closed-set fields for honest absence, not free text).

## `SpeechRequest`

| Field | Type | Rules | Requirement |
|---|---|---|---|
| `text` | `str` | min 1 after strip, max 5000 | FR-004 |
| `voice_id` | `str \| None` | must belong to a registered voice when given | FR-005 |
| `gender` | `Literal["male", "female"] \| None` | resolves to that gender's default voice when `voice_id` is absent | FR-002 |

Exactly one of `voice_id` or `gender` is expected in normal use; if both are given,
`voice_id` wins (explicit beats general, the same precedence rule 001's `resolve_voice`
already established for voice_id > locale > dialect).

## `LatencyInfo`

| Field | Type | Notes |
|---|---|---|
| `generation_ms` | `float` | Wall-clock time from provider-call start to audio fully received |
| `audio_duration_ms` | `float` | Duration of the produced audio |
| `real_time_factor` | `float` | `generation_ms / audio_duration_ms` — below 1.0 means faster than real time |

## `SpeechResponse`

| Field | Type | Notes | Requirement |
|---|---|---|---|
| `audio_base64` | `str` | Complete audio, base64-encoded | FR-006 |
| `content_type` | `str` | e.g. `audio/wave` | FR-006 |
| `voice` | `Voice` | Which voice actually served the request | FR-002 |
| `latency` | `LatencyInfo` | FR-007 |

---

## Relationships

```text
SpeechRequest ──resolved by──> voice lookup (voice_id, else gender's default) ──> Voice
     │
     ▼
GroqProvider.synthesize() ──> audio bytes
     │
     ├──> LatencyTrace ──> LatencyInfo
     └──────────────────────────────> SpeechResponse
```

## Validation Summary

| Rule | Enforced by | Requirement |
|---|---|---|
| Text non-empty after strip | Pydantic validator | FR-004 |
| Text ≤ 5000 chars | Pydantic `max_length` | FR-004 |
| `voice_id` belongs to a registered voice | Lookup + explicit rejection, alternatives named | FR-005 |
| Gender is a closed set, `"unknown"` representable | `Literal` type, never inferred | FR-009 |
| Credentials never serialized | No secret field on any model | FR-011-adjacent (Constitution VII, reused from 001) |
