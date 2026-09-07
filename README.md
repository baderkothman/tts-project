# لهجتنا — Arabic Dialect Text-to-Speech

Type Arabic text — Modern Standard or one of 13 real dialects — pick a voice by attribute
(gender, pitch, age) or clone one from a short reference clip, and hear it spoken. Powered
**exclusively** by [`oddadmix/lahgtna-omnivoice-v2`](https://huggingface.co/oddadmix/lahgtna-omnivoice-v2)
(the [OmniVoice](https://github.com/k2-fsa/OmniVoice) architecture), run locally through a
Python inference service. No Groq, ElevenLabs, Azure, OpenAI, Gemini, or any other TTS
provider — and no fallback to one.

This is the third phase of this repository's Arabic TTS work. The first two phases
(`specs/001-arabic-tts-prototype/`, `specs/002-saudi-tts-prototype/`) used hosted vendor
APIs (Edge, Groq, ElevenLabs); all of that code has been removed. See
`docs/TTS_MODEL_EVALUATION.md` for the (now superseded) reasoning behind phase 2's Groq
pick, kept as a historical record.

## Requires credentials?

**No.** The model downloads anonymously from Hugging Face Hub on first run (~2.4GB,
cached under `.hf_cache/` after that). `HF_TOKEN` in `.env.example` is optional — it only
raises the Hub's anonymous download rate limit, nothing else needs it.

## Architecture

```text
React + TypeScript (Vite)          FastAPI                          oddadmix/lahgtna-omnivoice-v2
   │  Arabic text + dialect/         │  loaded once at startup,         │  OmniVoice: Qwen3-0.6B
   │  voice options                  │  reused for every request        │  backbone + diffusion
   └──── multipart POST /api/tts ───►│──── model.generate(...) ────────►│  audio head, 24kHz
                                     │◄──── np.ndarray waveform ────────┘
   ◄──── audio/wav (base64) ─────────┘
```

- **Backend**: `backend/app/services/inference.py` owns the one `OmniVoice` instance for
  the process lifetime (loaded in a background thread at startup so `/api/health` responds
  immediately; inference itself is serialized behind a lock and run via `asyncio.to_thread`
  so it never blocks the event loop). Device is selected CUDA → MPS → CPU automatically.
- **Frontend**: `frontend/` — React 19 + TypeScript + Vite, RTL-first, no component
  framework — hand-built to a specific visual identity (see `frontend/DESIGN.md`).

## How dialect and voice actually work (no invented capabilities)

This model has **no fixed, named voice roster** — verified by reading the installed
`omnivoice` package's source, not assumed from marketing copy. Voice identity comes from
one of three real, mutually exclusive modes (`OmniVoice.generate()`):

1. **Voice design** — an `instruct` string built from a closed, validated vocabulary:
   gender (`male`/`female`), age, pitch, and whisper style. Passing anything outside that
   vocabulary raises an error inside the package itself — this app's UI only exposes what
   is actually in that enum.
2. **Voice cloning** — a 3–10s reference audio clip (+ optional transcript, auto-transcribed
   via Whisper if omitted).
3. **Auto** — the model picks a voice with no guidance.

**Dialect is a separate parameter** (`language`), not part of the voice-design instruct
string (an earlier assumption during this project that dialect would be an instruct
keyword was wrong — verified by reading the package's own instruct validator, which
rejects anything not in that gender/age/pitch/whisper/accent list). `backend/app/data/dialects.py`
maps each of the 13 dialects `oddadmix/lahgtna-omnivoice-v2`'s own model card marks
**completed** (not the six it marks merely *planned* — those are never exposed) to the
real ISO-ish language code the installed package's language resolver accepts. Two honest
gaps, not papered over:

- Palestinian, Lebanese, and Syrian share one underlying code (`apc`, Levantine Arabic) —
  the model has no distinct parameter for each; the dialectal vocabulary you actually type
  carries that distinction.
- Yemeni has no language code in the installed package at all, despite being on Lahgtna's
  own "completed" list. Selecting it falls back to language-agnostic mode with a warning
  surfaced in the UI, rather than silently pretending it's conditioned like the other 12.

`GET /api/voices` reflects this honestly too — it returns the real gender/pitch/age
options, not a fabricated list of named speakers.

## API

```text
GET  /api/health        status, whether the model finished loading, device
GET  /api/model-info    repo id, architecture, device, sample rate, capabilities
GET  /api/dialects      the 13 real dialects + MSA
GET  /api/voices        gender/pitch/age options (no named-voice roster — see above)
POST /api/tts           multipart/form-data: text + mode + dialect/voice options [+ ref_audio file]
```

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env   # optional — no credentials required

cd frontend && npm install
```

## Run

```bash
# Backend (loads the model once at startup — first run downloads ~2.4GB)
.venv/bin/uvicorn backend.app.main:app --reload --port 8000

# Frontend dev server (proxies /api to :8000, see frontend/vite.config.ts)
cd frontend && npm run dev
```

Open <http://localhost:5173>. For a single-process deployment, `npm run build` in
`frontend/` first — `backend/app/main.py` serves `frontend/dist/` directly from the same
FastAPI process at `/`, and `npm run dev` is then unnecessary.

## Tests

```bash
.venv/bin/pytest backend/tests -v -m "not integration"   # offline, no model weights: 28 pass
RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
                                                            # real weights, real MPS inference: 2 pass
```

The integration run above was executed during this phase's own development: model load
152s on first run (weight download included) on Apple Silicon (MPS), then real generation
at 0.98–2.16s for 1.6–2.7s of resulting audio (real-time factor 0.64–0.96 across dialects
and quality settings) — measured, not claimed.

## Known limitations

- Dialect ISO-code mapping (above) is inferred from the installed `omnivoice` package's
  language resolver plus Lahgtna's own model-card roadmap, not from a published
  Lahgtna-specific mapping document (none was found) — the 12 codes with distinct
  parameters were spot-checked with real generations across every dialect
  (`backend/tests/integration/test_live_model.py`); dialectal *authenticity* to a native
  speaker's ear was not evaluated by a rating panel.
- No streaming: `/api/tts` returns complete audio, matching the underlying package's
  `generate()` contract (batch, not chunked-and-streamed to the client).
- Reference-audio voice cloning is implemented and tested with synthetic WAV input in the
  contract suite; it has not been validated against real human reference clips of varying
  quality/noise in this session.
- `guidance_scale` and `num_step` (quality) are real, documented generation controls; the
  UI exposes quality (fast/high) but not guidance_scale, to keep the primary screen
  uncluttered — the backend still accepts and defaults it sensibly.

## Project layout

```text
backend/app/
├── api/tts.py            # /api/health, /api/model-info, /api/dialects, /api/voices, /api/tts
├── services/
│   ├── inference.py       # TTSEngine — the one OmniVoice instance, loaded once
│   ├── audio.py           # np.ndarray <-> WAV bytes, duration
│   └── fake_engine.py     # deterministic test double (no model weights needed)
├── models/tts.py          # TTSRequest/TTSResponse/ModelInfo/HealthResponse
└── data/
    ├── dialects.py         # the 13 real dialects + MSA, sourced as described above
    └── voice_design.py     # the real gender/pitch/age enum, read from the installed package

backend/tests/
├── unit/                   # dialect data integrity, request validation, audio math — offline
├── contract/                # API behavior against FakeEngine — offline, no model weights
└── integration/              # real model, real MPS/CUDA/CPU inference — opt-in, RUN_MODEL_INTEGRATION_TESTS=1

frontend/src/
├── App.tsx                 # orchestration + state
├── components/              # Header, TextComposer, DialectRail, VoicePanel,
│                             # ReferenceAudioUpload, GenerationControls, AudioPlayer, ErrorBanner
├── hooks/useWaveformPeaks.ts # real waveform from decoded audio, not decorative bars
└── api/client.ts             # typed fetch wrappers

docs/
├── TTS_MODEL_EVALUATION.md   # phase 2's Groq evaluation — superseded, kept as history
└── audio/                     # phase 2's sample audio — same status
specs/                         # Spec Kit planning artifacts for phases 1 and 2
```
