# Quickstart & Validation Guide

**Feature**: `001-arabic-tts-prototype`

How to run the prototype and verify each success criterion. Commands are exact.

## Prerequisites

- Python 3.12+
- Network access to the Microsoft Edge TTS endpoint (the credential-free default path)
- No API keys required for the default path

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env      # optional: only to enable Azure / ElevenLabs
```

## Run

```bash
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## Validation scenarios

Each maps to a success criterion in [spec.md](./spec.md). Contract details are in
[contracts/http-api.md](./contracts/http-api.md); shapes are in [data-model.md](./data-model.md).

### V1 — Hear Arabic speech (SC-001)

Enter `مرحباً بكم في تجربة تحويل النص العربي إلى كلام.` and press Generate.
**Expect**: intelligible Arabic audio, no configuration changed from defaults.

### V2 — Streaming starts before synthesis finishes (SC-002)

Submit a passage of 200+ Arabic characters to `POST /api/tts/stream`.
**Expect**: first bytes arrive well before the response completes; `X-TTS-Provider-TTFA-Ms`
is materially smaller than total elapsed time. Repeat 10 times; at least 9 must hold.

### V3 — Difficult content is verbalized correctly (SC-003)

`POST /api/preview` with text containing `125`, `1,250`, `25.5`, `75%`, `27/09/2026`,
`$25`, `1,250.50 دولار`, `API`, `د.`, and an Arabic/English mixed sentence.
**Expect**: every numeral, date, amount and abbreviation appears as Arabic words in
`processed`; each stage's contribution is visible in `stages`. No provider call needed.

### V4 — Preprocessing is fast (SC-004)

```bash
.venv/bin/pytest backend/tests/unit/test_pipeline_performance.py -v
```

**Expect**: P95 under 50 ms for a 500-character passage.

### V5 — Dialects differ audibly (SC-005)

Synthesize the same text with `dialect=msa` then `dialect=egyptian`.
**Expect**: different `X-TTS-Voice` values (`ar-SA-*` vs `ar-EG-*`) and audibly different speech.

### V6 — Styles differ or are reported unsupported (SC-006)

Synthesize identical text with `emotion` of `neutral`, `excited`, `calm`.
**Expect**: audibly different audio, and `X-TTS-Emotion-Native: false` — the honest signal
that Arabic voices expose no native style and prosody approximation was used.

### V7 — Benchmarks produce statistics files (SC-007)

```bash
.venv/bin/python -m backend.app.services.benchmark_service --provider edge --repetitions 5
```

**Expect**: `benchmarks/edge.json`, `benchmarks/results.json`, `benchmarks/comparison.csv`,
each carrying min/max/mean/median/P95 per stage plus provider, voice, sample set and timestamp.

### V8 — Pronunciation before/after (SC-008)

Open the demo panel, or `GET /api/pronunciation/demo`.
**Expect**: the observed defect with the provider and voice that produced it, and two
audibly different renderings from `/api/pronunciation/demo/audio?corrected=false|true`.

### V9 — Failure degrades, never crashes (SC-009)

```bash
.venv/bin/pytest backend/tests/unit/test_fallback.py -v
```

**Expect**: induced timeout and provider error each produce either fallback audio with
`used_fallback` true, or an actionable error. The service stays up in every case.

### V10 — Provider independence is structural (SC-010)

```bash
.venv/bin/pytest backend/tests/contract/test_import_boundaries.py -v
```

**Expect**: no provider SDK imported outside `backend/app/providers/`.

### V11 — No secret leakage (SC-011)

```bash
.venv/bin/pytest backend/tests/contract/test_no_secret_leak.py -v
```

### V12 — Markup cannot alter instructions (SC-012)

```bash
.venv/bin/pytest backend/tests/unit/test_ssml_injection.py -v
```

**Expect**: SSML-like user text is escaped and spoken literally.

### V13 — Full suite runs without credentials (SC-015)

```bash
.venv/bin/pytest backend/tests -v
```

**Expect**: passes with integration tests reported as **skipped**, not failed.

## Enabling credential-gated providers

Set in `.env`: `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`, and/or `ELEVENLABS_API_KEY`.
Restart. `GET /api/providers` should move them from `missing_credentials` to `available`.
Then:

```bash
.venv/bin/pytest backend/tests/integration -v -m integration
```
