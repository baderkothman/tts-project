# Saudi Arabic Text-to-Speech Prototype

A deliberately small, Python-first Saudi Arabic TTS prototype: enter Saudi Arabic text,
pick a male or female voice, hear real Saudi-dialect speech, see how long it took. This is
a narrower, second phase of the original Arabic TTS work
(`specs/001-arabic-tts-prototype/`) — pronunciation correction, diacritization,
multi-dialect routing, and the Hugging Face experimentation layer have all been
deliberately removed for this phase; see `specs/002-saudi-tts-prototype/spec.md` for the
full scope decision and `docs/TTS_MODEL_EVALUATION.md` for why Groq was selected over every
alternative actually tested.

## Requires credentials?

**Yes, unlike the prior feature.** This phase's one provider — Groq's Orpheus Arabic model,
genuinely Saudi/Gulf-dialect-trained — needs an API key. There is no credential-free
default path in this phase.

> **Note on Azure**: this project still does not use Microsoft Azure AI Speech anywhere,
> unchanged from the prior feature's hard project-wide constraint.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env
# edit .env: set GROQ_API_KEY (https://console.groq.com)
```

## Run

```bash
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>. Type Saudi Arabic text, choose a gender, optionally pick a
specific voice, and press **توليد الصوت**.

## Tests

```bash
.venv/bin/pytest backend/tests -v -m "not integration"  # offline, no credentials needed: 24 pass
.venv/bin/pytest backend/tests/integration -v -m integration  # live Groq calls; skips without GROQ_API_KEY
```

## Project layout

```text
backend/app/
├── api/speak.py       # POST /api/speak, GET /api/voices
├── providers/          # TTSProvider ABC + groq.py (sole adapter) + fake.py (test double)
├── services/           # voice_resolution.py, latency.py
├── models/             # Voice, SpeechRequest, SpeechResponse, LatencyInfo
└── data/voices.py      # The 6 real Groq Saudi voices (3 male, 3 female)

backend/tests/
├── unit/                # Provider, latency, voice-resolution logic — offline
├── contract/            # API behavior, no-secret-leak
└── integration/          # One live Groq call, credential-gated

frontend/index.html      # One static page, no build step, no domain logic
docs/
├── TTS_MODEL_EVALUATION.md  # The real comparison behind the provider selection
└── audio/                    # Real generated sample audio (male + female)
specs/002-saudi-tts-prototype/  # Spec Kit planning artifacts for this phase
```

## Final decision report

```text
Best Saudi TTS:
Groq — Orpheus Arabic (canopylabs/orpheus-arabic-saudi)

Why:
The only candidate that is simultaneously genuinely dialect-trained (not MSA), offers
real male AND female voices without needing a reference-audio clip this project has no
right to use, needs no local GPU, and was live-tested end to end with real latency
numbers before the decision was made.

Best male voice:
Abdullah (one of three: Abdullah, Fahad, Sultan)

Best female voice:
Lulwa (one of three: Lulwa, Noura, Aisha)

Other voices available:
Fahad, Sultan (male); Noura, Aisha (female) — 6 total, all real, none fabricated

Model/API:
Groq hosted API, model canopylabs/orpheus-arabic-saudi

Local or hosted:
Hosted — no GPU or local model management required

Average generation latency:
~615ms across 3 repeated live calls (569.8-684.5ms), for ~2.4s of resulting audio
(real-time factor ~0.24-0.29 — faster than the audio's own playback duration)

Cost:
Groq's standard API pricing (pay-per-request; no separate model license fee)

Main limitation:
A real, vendor-undocumented 10 requests/minute rate limit on this model (found by
exceeding it live in the prior feature) — the adapter absorbs one transient hit with a
bounded, Retry-After-honoring retry, but a second failure within the window surfaces as
a clear 502, not a crash. Also: only one Hugging Face candidate (NAMAA-Saudi-TTS) was
actually reachable without heavier dependencies or rights issues, and even that one
offers only one gender for free — genuinely comparing a locally-hosted Saudi model with
both defensible genders remains a real gap for a future iteration.
```

## Known limitations

- Groq's Orpheus Arabic dialect *authenticity* (does it actually sound like colloquial
  Saudi speech to a native speaker) remains a vendor claim plus this session's own
  generated-audio evidence — no native-speaker rating panel was available in this
  environment (`docs/TTS_MODEL_EVALUATION.md`).
- A real, vendor-undocumented 10 requests/minute rate limit exists on this model; the
  adapter absorbs one transient hit with a bounded retry, and reports a clear error on a
  second failure rather than crashing or hanging.
- No streaming: the adapter synthesizes the complete audio (chunked internally to respect
  the vendor's 200-character-per-call limit) before returning it as one unit — matching
  what the prior feature already confirmed absent, not re-investigated here.
- This phase intentionally has no pronunciation correction, diacritization, dialect
  detection, or Arabic text preprocessing beyond what Groq's own 200-character chunking
  needs — out of scope per spec.md FR-012, not an oversight.
