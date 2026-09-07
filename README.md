# Arabic Text-to-Speech Prototype

A Python-first Arabic TTS prototype: enter Arabic text, hear streaming Arabic
speech, with Arabic-aware preprocessing (numbers, dates, currencies,
abbreviations, code-switching), pronunciation correction, multi-provider
routing, and measured latency — the first stage toward a real-time Arabic
conversational avatar. Full planning artifacts under `specs/001-arabic-tts-prototype/`.

## Requires credentials?

**No, for the default path.** The default provider, Microsoft Edge Neural
TTS, needs no API key. Azure AI Speech and ElevenLabs are implemented but
credential-gated — they report themselves as `missing_credentials` (not an
error) until you configure them.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

## Run

```bash
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. Type Arabic text, click **توليد الصوت (بث)** to
hear streaming speech, or **معاينة النص المعالج فقط** to see the processed
text without synthesizing audio.

## Enable Azure / ElevenLabs

```bash
cp .env.example .env
# edit .env: set AZURE_SPEECH_KEY + AZURE_SPEECH_REGION, and/or ELEVENLABS_API_KEY
```

Restart the server; `GET /api/providers` will show them as `available`.

## Tests

```bash
.venv/bin/pytest backend/tests -v              # full suite (104 tests, fully offline)
.venv/bin/pytest backend/tests -v -m "not integration"  # explicit offline-only
.venv/bin/pytest backend/tests/integration -v -m integration  # live calls; skips what's not configured
```

The default suite makes **no live network calls** and needs no credentials
(Constitution VIII). Integration tests are separately marked and skip
(not fail) when their provider's credentials are absent.

## Benchmark

```bash
.venv/bin/python -m backend.app.services.benchmark_service --provider edge --repetitions 5
```

Writes `benchmarks/edge.json`, `benchmarks/results.json`,
`benchmarks/comparison.csv` — per-stage min/max/mean/median/P95. Real output
from this repo's own run is in `docs/BENCHMARK_RESULTS.md`.

## Pronunciation demo

```bash
.venv/bin/python scripts/observe_pronunciation.py   # regenerates docs/audio/*.mp3
```

Then visit the demo panel on the running page, or
`GET /api/pronunciation/demo` / `GET /api/pronunciation/demo/audio?corrected=true|false`.
Full case writeup, including an explicit disclosure of what was and wasn't
independently verifiable in this environment: `docs/PRONUNCIATION.md`.

## Project layout

```text
backend/app/
├── api/              # FastAPI routes: tts, voices, benchmark, pronunciation
├── providers/        # TTSProvider ABC + edge/azure/elevenlabs/fake adapters
├── text_processing/  # Pure-function Arabic pipeline (normalize→dates→
│                      currencies→numbers→abbreviations→code-switching→
│                      pronunciation)
├── services/         # Orchestration, voice routing, latency, benchmarking
├── models/           # Pydantic request/response/voice/benchmark models
└── data/             # Voice catalogue (16 Arabic locales), sample set

backend/tests/
├── unit/             # Text-processing, models, latency, statistics — offline
├── contract/         # API + provider-interface conformance, import
│                      boundaries, no-secret-leak, no-text-logging
└── integration/       # Live provider calls — credential-gated, skip if absent

frontend/index.html   # One static page, no build step, no domain logic
scripts/               # observe_pronunciation.py
benchmarks/             # Generated benchmark output
docs/                   # Evaluation, test cases, pronunciation, benchmarks,
                         # production architecture
specs/001-arabic-tts-prototype/  # Full Spec Kit planning artifacts
```

## Known limitations

- Only `edge` has live-measured benchmark data in this repo; Azure/ElevenLabs
  adapters are implemented and contract-tested but weren't exercised live (no
  credentials in the implementation environment) — see
  `docs/BENCHMARK_RESULTS.md`.
- The pronunciation demo's specific mispronunciation claim was not
  perceptually re-confirmed by an ASR tool (none was available in this
  environment) — the demo is built on real generated audio and a
  well-documented linguistic ambiguity, with the gap disclosed explicitly in
  `docs/PRONUNCIATION.md`.
- Automatic full diacritization (tashkeel) is out of scope by design
  (Assumptions in spec.md) — pronunciation correction uses targeted rules.
- Rate limiting is architecture-only (documented in
  `docs/PRODUCTION_ARCHITECTURE.md`), not implemented, per FR-042a.
