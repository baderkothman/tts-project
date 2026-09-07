# Arabic Text-to-Speech Prototype

A Python-first Arabic TTS prototype: enter Arabic text, hear streaming Arabic
speech, with Arabic-aware preprocessing (numbers, dates, currencies,
abbreviations, code-switching), pronunciation correction, multi-provider
routing, and measured latency — the first stage toward a real-time Arabic
conversational avatar. Full planning artifacts under `specs/001-arabic-tts-prototype/`.

## Requires credentials?

**No, for the default path.** The default provider, Microsoft Edge Neural
TTS, needs no API key. Groq (Orpheus Arabic — genuine Saudi dialect),
ElevenLabs, and Hugging Face (dialect detection, and an experimental
Egyptian-dialect TTS candidate) are implemented but credential-gated — they
report themselves as `missing_credentials` (not an error) until you
configure them.

> **Note on Azure:** this project deliberately does **not** use Microsoft
> Azure AI Speech anywhere — not as a provider, a fallback, or an
> architecture recommendation — per the individual-developer accessibility
> constraint in `specs/001-arabic-tts-prototype/spec.md`. Microsoft Edge
> Neural TTS (above) is a separate, credential-free endpoint that requires no
> Azure account or tenant; it is not the Azure Speech service.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cd frontend && npm install && cd ..
```

## Run in development

```bash
# Terminal 1
.venv/bin/uvicorn backend.app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` to FastAPI. Type Arabic text,
click **ولّد الصوت** to hear streaming speech, or **عاين المعالجة** to inspect
the processed text without synthesizing audio.

For the single-server production path, build React first and then open
<http://127.0.0.1:8000>:

```bash
cd frontend && npm run build && cd ..
.venv/bin/uvicorn backend.app.main:app --port 8000
```

## Enable Groq / ElevenLabs / Hugging Face

```bash
cp .env.example .env
# edit .env: set GROQ_API_KEY, ELEVENLABS_API_KEY, and/or HF_TOKEN
```

Restart the server; `GET /api/providers` will show them as `available`.
`HF_TOKEN` (a Hugging Face access token, read-only scope is enough) enables
`POST /api/dialect/resolve` and `/compare`'s automatic dialect classifier and
the experimental Hugging Face voice; without it, both endpoints still work —
they fall back to the pronunciation dictionary and an existing provider
respectively, and say so explicitly (FR-057).

## Tests

```bash
.venv/bin/pytest backend/tests -v   # full suite: 186 pass, 2 skip w/o HF_TOKEN (0 fail)
.venv/bin/pytest backend/tests -v -m "not integration"  # explicit offline-only
.venv/bin/pytest backend/tests/integration -v -m integration  # live calls; skips what's not configured
cd frontend && npm test             # React components and typed API client
cd frontend && npm run build        # TypeScript + production bundle
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
├── api/              # FastAPI routes: tts, voices, benchmark, pronunciation,
│                      dialect (resolve/compare — US6-7)
├── providers/        # TTSProvider ABC + edge/groq/elevenlabs/fake adapters,
│                      huggingface/ (provider + local/inference_api/endpoint backends)
├── text_processing/  # Pure-function Arabic pipeline (normalize→dates→
│                      currencies→numbers→abbreviations→code-switching→
│                      pronunciation), huggingface/ (dialect classifier,
│                      diacritizer, G2P, pronunciation model, model registry)
├── services/         # Orchestration, voice routing, latency, benchmarking,
│                      dialect_service (resolve/compare, HF fallback routing)
├── models/           # Pydantic request/response/voice/benchmark models,
│                      dialect.py (DialectProfile, HFModelConfig, etc.)
└── data/             # Voice catalogue (16 Arabic locales), sample set,
                       dialect_profiles, pronunciation_dictionary, hf_model_registry

backend/tests/
├── unit/             # Text-processing, models, latency, statistics — offline
├── contract/         # API + provider-interface conformance, import
│                      boundaries, no-secret-leak, no-text-logging
└── integration/       # Live provider calls — credential-gated, skip if absent

frontend/             # React + TypeScript UI; Vite emits dist/ for FastAPI,
                      # with no routing or linguistic domain logic in the browser
scripts/               # observe_pronunciation.py
benchmarks/             # Generated benchmark output
docs/                   # Evaluation, dialect evaluation, voice catalog, test
                         # cases, pronunciation, benchmarks, production architecture,
                         # HF_MODEL_RESEARCH.md, PRONUNCIATION_EVALUATION.md
specs/001-arabic-tts-prototype/  # Full Spec Kit planning artifacts
```

## Known limitations

- `edge`, `groq`, and `elevenlabs` all have live-measured benchmark data
  (`docs/BENCHMARK_RESULTS.md`) — all three providers are fully live-verified. Getting
  ElevenLabs working required two real fixes, not just setting the key: the configured API
  key was initially scoped without `voices_read` (401 on listing voices) until that
  permission was granted, and the originally-catalogued "Rachel" voice turned out to be a
  public "Voice Library" voice the free tier can't call via the API (402) — only voices
  already in the account's own library work on the free tier. Replaced with "Sarah", one of
  the account's default premade voices, confirmed live before adopting it. `ProviderError`
  gained a distinct `payment_required` kind for this class of failure (as opposed to an
  invalid key or a malformed request — `backend/app/providers/base.py`), so a future account
  restriction like this fails clearly instead of masquerading as a generic bad request.
- **Groq's Orpheus Arabic model enforces a real 10 requests/minute limit** (confirmed live
  via `x-ratelimit-*` response headers; not documented on the model's page fetched during
  research) — a benchmark run or a busy conversational session can exhaust it in well under
  a minute. The adapter retries once, honoring the vendor's `Retry-After` header, which
  recovered most but not all of a full 11-sample benchmark run — see
  `docs/BENCHMARK_RESULTS.md` for the exact run where this is shown, not hidden.
- The pronunciation demo's specific mispronunciation claim was not
  perceptually re-confirmed by an ASR tool (none was available in this
  environment) — the demo is built on real generated audio and a
  well-documented linguistic ambiguity, with the gap disclosed explicitly in
  `docs/PRONUNCIATION.md`.
- Automatic full diacritization (tashkeel) is out of scope by design
  (Assumptions in spec.md) — pronunciation correction uses targeted rules.
- Rate limiting is architecture-only for THIS service's own API (documented in
  `docs/PRODUCTION_ARCHITECTURE.md`), not implemented, per FR-042a — separate from Groq's
  own upstream rate limit above, which this project's adapter does handle (bounded retry).
- Groq's Orpheus Arabic dialect *authenticity* (does it actually sound like colloquial
  Saudi speech to a native speaker) remains a vendor claim, not perceptually re-verified —
  no ASR/human-rating tool is available in this environment, only byte-level/latency
  measurement — see `docs/DIALECT_EVALUATION.md`.
- Groq's adapter has no incremental streaming (confirmed absent live, not merely
  undocumented); it synthesizes the complete audio internally (chunked to respect the
  vendor's 200-char-per-call limit) before yielding it as one unit.
- **Hugging Face dialect/pronunciation layer (US6-7) is implemented and both live- and
  offline-tested; the two enabled models are confirmed live-blocked by the platform, not
  by credentials.** With a real `HF_TOKEN` (correctly permissioned —
  `inference.serverless.write` — after an initial 403 from a token scoped only to
  `repo.content.read`, the same class of gap as the earlier ElevenLabs `voices_read` fix),
  both the text dialect classifier and `oddadmix/chatterbox-egyptian-v0` were actually
  called and both are genuinely not deployed on any Hugging Face Inference Provider (`400`/
  `410` from Hugging Face itself, model metadata confirms `inference: null`) — a real
  platform constraint for niche community models, not a code defect. Both degrade honestly
  (`unavailable_reason` stated, existing-provider fallback used) and the integration tests
  skip with the exact confirmed reason rather than fail. A separate real bug — a stale,
  DNS-dead legacy Hugging Face hostname (`api-inference.huggingface.co`) hardcoded in the
  raw-`httpx` linguistic-processing calls — was found and fixed along the way. See
  `docs/HF_MODEL_RESEARCH.md` and `docs/DIALECT_EVALUATION.md`'s "Hugging Face" section for
  the full finding; using either model in production would need a paid Dedicated Inference
  Endpoint or local execution, not just a token.
- The Hugging Face diacritization and G2P candidates (`docs/HF_MODEL_RESEARCH.md`) are
  structurally wired but left `enabled=False` in the registry pending license confirmation
  — a deliberate FR-058 gate, not an oversight; the pronunciation-dictionary layer
  (`data/pronunciation_dictionary.py`) is live and does not depend on them.
- `GET /api/pronunciation/demo` and `POST /api/dialect/compare` are both real and tested but
  do not share one implementation as originally planned (plan.md Design Decision 8) — that
  refactor was deliberately deferred to avoid destabilizing the already-tested Story 5 demo
  endpoint; they currently duplicate a small amount of comparison-assembly logic.
