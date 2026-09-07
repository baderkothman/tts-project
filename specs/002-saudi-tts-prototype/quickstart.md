# Quickstart & Validation Guide

**Feature**: `002-saudi-tts-prototype`

## Prerequisites

- Python 3.12+
- A Groq API key (`GROQ_API_KEY`) — this phase's one provider is credential-gated, unlike
  the prior feature's credential-free default path (spec.md Assumptions)

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env      # set GROQ_API_KEY
```

## Run

```bash
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## Validation scenarios

### V1 — Male voice produces audio (SC-002)

```bash
curl -sX POST http://127.0.0.1:8000/api/speak \
  -H 'Content-Type: application/json' \
  -d '{"text": "وش رايك نطلع نتعشى اليوم؟", "gender": "male"}'
```

**Expect**: `200`, `voice.gender == "male"`, non-empty `audio_base64`, a complete
`latency` object.

### V2 — Female voice produces audio (SC-002)

Same request with `"gender": "female"`. **Expect**: `voice.gender == "female"`, and the
resulting audio is audibly distinct from V1's when played.

### V3 — Empty text rejected (FR-004)

```bash
curl -sX POST http://127.0.0.1:8000/api/speak -H 'Content-Type: application/json' -d '{"text": ""}'
```

**Expect**: `422`.

### V4 — Unknown voice rejected (FR-005)

```bash
curl -sX POST http://127.0.0.1:8000/api/speak \
  -H 'Content-Type: application/json' \
  -d '{"text": "مرحبا", "voice_id": "not-a-real-voice"}'
```

**Expect**: `400`, body names the valid voice ids.

### V5 — Latency is always reported (SC-003)

Inspect any `200` response from V1/V2 — `latency.generation_ms`, `latency.audio_duration_ms`,
and `latency.real_time_factor` must all be present and numeric.

### V6 — Offline test suite passes without credentials (Constitution VIII)

```bash
.venv/bin/pytest backend/tests -v -m "not integration"
```

**Expect**: passes fully offline, using `FakeProvider`.

### V7 — Live Groq integration test (credential-gated)

```bash
.venv/bin/pytest backend/tests/integration -v -m integration
```

**Expect**: runs a real synthesis if `GROQ_API_KEY` is set; skips (not fails) otherwise.
