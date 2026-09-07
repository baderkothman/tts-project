# Contract: HTTP API

**Feature**: `002-saudi-tts-prototype` | Base: `http://127.0.0.1:8000`

All request bodies are Pydantic-validated; a violation returns `422` with field detail.
No endpoint ever returns a credential value.

---

## `GET /api/voices`

Returns every registered `Voice`, grouped implicitly by `gender` (the frontend groups
client-side; the API returns a flat list — no server-side grouping logic needed for six
items).

## `POST /api/speak`

Body: `SpeechRequest` (`text`, and either `voice_id` or `gender`). Returns `200` with
`SpeechResponse` (`audio_base64`, `content_type`, `voice`, `latency`).

Errors:
- `422` — empty/whitespace text, or text over 5000 chars.
- `400` — `voice_id` not registered; body names the valid ids for the requested (or
  default) gender.
- `502` — provider error (timeout, rate limit, server error) — `detail` states the kind
  plainly (e.g. "Groq rate limit exceeded (10 requests/minute)"), never a raw vendor
  exception, never a credential value.

## `GET /health`

`{"status": "ok", "provider_available": true|false}`.

## `GET /`

Serves the static demonstration page.

---

## Cross-cutting contract tests

| ID | Assertion | Requirement |
|---|---|---|
| AC-01 | Empty/whitespace text → `422` | FR-004 |
| AC-02 | Unregistered `voice_id` → `400` listing valid ids for the resolved gender | FR-005 |
| AC-03 | Male voice request → `200`, `voice.gender == "male"` | FR-002 |
| AC-04 | Female voice request → `200`, `voice.gender == "female"` | FR-002 |
| AC-05 | Every `200` response carries a complete `LatencyInfo` | FR-007 |
| AC-06 | No response body or header contains a credential | Constitution VII |
| AC-07 | Provider timeout/error/rate-limit → `502` with a clear, distinguishable `detail`, never a crash | FR-008 |
