# لهجتنا — Arabic Dialect Text-to-Speech

Type Arabic text — Modern Standard or one of 13 real dialects, optionally mixed with
English — pick a voice by attribute (gender, pitch, age) or clone one from a short
reference clip, and hear it spoken with automatic diacritization and natural-sounding
embedded English. Powered **exclusively** by
[`oddadmix/lahgtna-omnivoice-v2`](https://huggingface.co/oddadmix/lahgtna-omnivoice-v2)
(the [OmniVoice](https://github.com/k2-fsa/OmniVoice) architecture) for Arabic speech, run
locally through a Python inference service. No Groq, ElevenLabs, Azure, OpenAI, Gemini, or
any other hosted TTS provider — and no fallback to one. (Kokoro-82M, also local and
open-source, is used only as a selectable *alternative* for English words — see
[Mixed Arabic/English speech](#mixed-arabicenglish-speech) below.)

This is the third phase of this repository's Arabic TTS work. The first two phases
(`specs/001-arabic-tts-prototype/`, `specs/002-saudi-tts-prototype/`) used hosted vendor
APIs (Edge, Groq, ElevenLabs); all of that code has been removed. See
`docs/TTS_MODEL_EVALUATION.md` for the (now superseded) reasoning behind phase 2's Groq
pick, kept as a historical record.

## Requires credentials?

**No.** Both models download anonymously from Hugging Face Hub on first run (Lahgtna
~2.4GB, the diacritizer ~1.2GB, cached under `.hf_cache/` after that; Kokoro-82M is much
smaller). `HF_TOKEN` in `.env.example` is optional — it only raises the Hub's anonymous
download rate limit, nothing else needs it. One system dependency: `espeak-ng`
(`brew install espeak-ng` / `apt install espeak-ng`), needed for Kokoro's phonemizer and
for the English-transliteration fallback — see below.

## Architecture

```text
React + TypeScript (Vite)          FastAPI                                    Lahgtna (Arabic) + Kokoro (English, optional)
   │  Arabic/mixed text +             │  text_preprocessor: overrides,           │
   │  dialect/voice/pipeline           │  normalize, segment, diacritize          │
   │  options                          │           │                             │
   └──── multipart POST /api/tts ───► │  speech_pipeline: 1 Lahgtna call,        │
                                       │  or Lahgtna+Kokoro+audio_merger ───────► │
                                       │◄──── np.ndarray waveform(s) ─────────────┘
   ◄──── audio/wav (base64) +          │
         processed text + segments ───┘
```

- **Backend**: `backend/app/services/inference.py` owns the one `OmniVoice` instance for
  the process lifetime (loaded in a background thread at startup so `/api/health` responds
  immediately; inference itself is serialized behind a lock and run via `asyncio.to_thread`
  so it never blocks the event loop). Device is selected CUDA → MPS → CPU automatically.
  `services/text_preprocessor.py` and `services/speech_pipeline.py` sit in front of it —
  see the two sections below for what they actually do and why.
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

## Automatic diacritization (تشكيل)

Arabic text is automatically diacritized before it reaches Lahgtna, via
`basharalrfooh/Fine-Tashkeel` (a ByT5 fine-tune with a published DER of 0.95%/WER 2.49% —
see `docs/DIACRITIZATION_EVALUATION.md` for why this model was picked over three other
real candidates). Two policies exist because of defects actually reproduced while building
this, not caution for its own sake:

- **Text that already has any diacritic is never re-diacritized.** Running the model on
  already-vocalized input was tested directly and corrupts it (doubled shaddas/dammas) —
  so a user's own تشكيل is always preserved untouched, not just as a politeness rule.
- **For any non-MSA dialect, the model's word-final grammatical case endings (i'rab) are
  stripped**, keeping internal stem vowels. Tested directly on real Lebanese/Gulf
  sentences: the model otherwise appends full MSA case endings dialectal speech doesn't
  use — e.g. colloquial "روح" ("go") came back "رُوحٍ", a genitive-case noun reading
  ("spirit/soul"). Full before/after examples in `docs/DIACRITIZATION_EVALUATION.md`.

## Mixed Arabic/English speech

Set via `pipeline_mode` on `POST /api/tts` (and previewable with no audio cost via
`POST /api/preprocess`):

| Mode | What happens |
|---|---|
| `native` (default) | Arabic/English segmentation still runs (for the UI preview and pronunciation overrides), but the whole pronunciation-ready text goes through **one** Lahgtna call — no second model, no stitching. |
| `dual_model` | Arabic segments → Lahgtna; English segments → Kokoro-82M (Apache-2.0, 24kHz — same rate as Lahgtna, so no resampling); segments stitched with loudness-matching + a short crossfade (`services/audio_merger.py`). Falls back to `native` (with a warning) if Kokoro isn't loaded, or if voice cloning is active (a cloned voice's whole identity would be broken by splicing in Kokoro's fixed voice). |
| `transliteration` | English words are converted to Arabic-script phonetics first (`services/transliterator.py`, via real `espeak-ng` phonemization — not naive letter spelling: "development" → "ديڤيلبمنت", "React" → "رياكت"), then spoken as one Lahgtna call. |

`native` is the default because it tested best, not by assumption — see
`docs/ENGLISH_TTS_EVALUATION.md` for the actual ASR-round-trip measurements behind that
choice. `dual_model` and `transliteration` are fully implemented, real, and selectable —
useful when a specific sentence's English comes out wrong in `native` mode.

Language segmentation (`services/language_segmenter.py`) is pure Unicode-script detection —
no model, no LLM call — and merges adjacent same-language runs so "development team" stays
one English segment rather than splitting per word; see its module docstring for the exact
algorithm and `backend/tests/unit/test_language_segmenter.py` for the worked examples.

Known mispronunciations (names, brands, acronyms) can be fixed permanently without touching
any code: add an entry to `backend/app/data/pronunciation_overrides.json`
(`{"term": "Arabic-script pronunciation"}`) — it's applied before segmentation, so the term
is simply spoken as Arabic from then on.

## API

```text
GET  /api/health        status, whether Lahgtna finished loading, device
GET  /api/model-info    repo id, architecture, device, sample rate, capabilities, pipeline modes,
                         diacritizer/English-TTS load status
GET  /api/dialects      the 13 real dialects + MSA
GET  /api/voices        gender/pitch/age options (no named-voice roster — see above)
POST /api/preprocess    JSON: text + dialect_id + pipeline_mode -> processed text + per-segment
                         breakdown, no audio generated (the UI's live preview)
POST /api/tts           multipart/form-data: text + mode + pipeline_mode + dialect/voice options
                         [+ ref_audio file] -> audio + the same processed-text/segments breakdown
POST /api/tts/stream    same request shape as /api/tts -> Server-Sent Events, one `chunk` per
                         sentence as its audio is ready, then a `done` event with real measured
                         time-to-first-audio (`ttfa_ms`) — see "Streaming and latency" below
```

## Streaming and latency

`OmniVoice.generate()` has no incremental/token-level API — it's a blocking call that
returns a whole clip's audio only once every bit of it is decoded (verified by reading the
installed package's public surface). `services/sentence_splitter.py` +
`SpeechPipeline.synthesize_stream` work around that the only way available: splitting the
already-diacritized text on sentence boundaries and calling `generate()` once per sentence,
returning each one's audio over `POST /api/tts/stream` (Server-Sent Events) as soon as it's
ready — real time-to-first-audio instead of only whole-clip latency. The frontend's
"تجربة البث التدريجي" button (`components/StreamingDemo.tsx`,
`hooks/useStreamingSynthesis.ts`) plays each chunk gapless via the Web Audio API and shows
the live number.

Real measured results (not estimated) from `scripts/benchmark_tts.py` are in
`docs/PERFORMANCE_BENCHMARKS.md`: 66–83% faster time-to-first-sound on multi-sentence text,
correctly ~0% on single-sentence text (one sentence has no earlier chunk to return sooner).
Streaming is deliberately scoped to one engine — `native`'s Lahgtna-only path — regardless
of the request's `pipeline_mode`; `dual_model`'s per-segment Kokoro routing doesn't compose
with resplitting into sentences, so a non-`native` request streams with a warning instead.

This is still per-sentence *batch* generation, not true token-level streaming — see
`docs/PRODUCTION_ARCHITECTURE.md` for what a production system feeding this from a live LLM
token stream (rather than a complete pre-written string) would look like, and what would
have to change.

## Setup

```bash
brew install espeak-ng   # or: apt install espeak-ng — needed by Kokoro + the transliteration fallback
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env   # optional — no credentials required

npm install   # root install — sets up both frontend/ and backend/ as npm workspaces (see below)
```

## Run

This is a [Turborepo](https://turborepo.com) — a root `package.json` with `frontend/` and
`backend/` as npm workspaces, orchestrated by `turbo.json`. `backend/package.json` is a thin
task-runner shim only (the real backend is Python; it has no build step and no JS code) —
it exists purely so `turbo run dev`/`test` can start/run it alongside the frontend from one
root command instead of two separate terminals.

```bash
npm run dev     # starts both: backend on :8000 (loads the model, first run downloads ~2.4GB)
                 #              and frontend on :5173 (proxies /api to :8000)
```

Open <http://localhost:5173>. Prefer separate terminals, or want just one side? Run either
piece directly — `.venv/bin/uvicorn backend.app.main:app --reload --port 8000`, or
`cd frontend && npm run dev` — exactly as before; `npm run dev` at the root is a convenience,
not a requirement. For a single-process deployment, `npm run build` (root, or `cd frontend &&
npm run build`) first — `backend/app/main.py` serves `frontend/dist/` directly from the same
FastAPI process at `/`, and `npm run dev` is then unnecessary.

## Tests

```bash
.venv/bin/pytest backend/tests -v -m "not integration"   # offline, no model weights: 101 pass
RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
                                                            # real weights, real MPS inference: 6 pass

npm run test    # root — same offline suite via turbo, cached on unchanged inputs (turbo run test)
npm run build   # root — frontend's tsc+vite build; backend has no build step, turbo skips it
npm run lint    # root — frontend's oxlint; backend has no linter configured, turbo skips it
```

The integration runs were executed during this phase's own development: Lahgtna load
152s on first run (weight download included) on Apple Silicon (MPS), then real generation
at 0.98–4.7s per sentence across native/dual_model/transliteration pipeline modes and every
dialect (real-time factor 0.6–1.0) — measured, not claimed. The offline suite mocks the
diacritizer and (where relevant) Kokoro so it never needs model weights or `espeak-ng`
present, except `test_transliterator.py`, which calls real `espeak-ng` (lightweight, no
model download) and skips itself if the system library isn't installed.

## Known limitations

- Dialect ISO-code mapping (above) is inferred from the installed `omnivoice` package's
  language resolver plus Lahgtna's own model-card roadmap, not from a published
  Lahgtna-specific mapping document (none was found) — the 12 codes with distinct
  parameters were spot-checked with real generations across every dialect
  (`backend/tests/integration/test_live_model.py`); dialectal *authenticity* to a native
  speaker's ear was not evaluated by a rating panel.
- `/api/tts` itself is still batch (matches `generate()`'s own contract — one full clip per
  call); `/api/tts/stream` is sentence-chunked, not token-level, streaming — see "Streaming
  and latency" above and `docs/PRODUCTION_ARCHITECTURE.md` for what real streaming
  generation would require that this model doesn't expose.
- Reference-audio voice cloning is implemented and tested with synthetic WAV input in the
  contract suite; it has not been validated against real human reference clips of varying
  quality/noise in this session.
- `guidance_scale` and `num_step` (quality) are real, documented generation controls; the
  UI exposes quality (fast/high) but not guidance_scale, to keep the primary screen
  uncluttered — the backend still accepts and defaults it sensibly.
- The diacritizer's non-MSA fix (stripping word-final case endings) is a targeted fix for
  one reproduced defect, not a general dialectal diacritizer — see
  `docs/DIACRITIZATION_EVALUATION.md`'s closing section for exactly what is and isn't
  claimed.
- The `native` vs `dual_model` vs `transliteration` default was decided by an ASR
  round-trip proxy (Whisper transcribing the generated audio back), not a
  native-speaker/native-English-listener panel — see `docs/ENGLISH_TTS_EVALUATION.md`.
- The phonetic transliterator (`services/transliterator.py`) is a real espeak-ng-driven
  approximation, not a perfect G2P->Arabic system — unusual OOV spellings may come out
  imperfect; `pronunciation_overrides.json` is the intended fix for any specific term.

## Project layout

```text
package.json / turbo.json   # root Turborepo config — see "Run" above
backend/package.json        # task-runner shim only (dev/test) — no build/lint script, no JS code
backend/app/
├── api/tts.py               # /api/health, /api/model-info, /api/dialects, /api/voices,
│                             # /api/preprocess, /api/tts
├── services/
│   ├── inference.py          # TTSEngine — the one OmniVoice (Arabic) instance, loaded once
│   ├── english_tts.py         # Kokoro-82M wrapper, for dual_model mode
│   ├── diacritizer.py         # Fine-Tashkeel wrapper — see docs/DIACRITIZATION_EVALUATION.md
│   ├── language_segmenter.py  # pure Unicode-script Arabic/English segmentation, no model
│   ├── transliterator.py      # espeak-ng-driven phonetic EN->Arabic-script fallback
│   ├── pronunciation_dictionary.py  # JSON-backed term overrides, applied before segmentation
│   ├── audio_merger.py        # loudness/rate-matching + crossfade stitching for dual_model
│   ├── sentence_splitter.py   # splits processed text into sentence chunks for /api/tts/stream
│   ├── text_preprocessor.py   # orchestrates all of the above into one pronunciation-ready pass
│   ├── speech_pipeline.py     # orchestrates text_preprocessor + engines into final audio,
│   │                          # incl. synthesize_stream() for sentence-chunked streaming
│   ├── audio.py                # np.ndarray <-> WAV bytes, duration
│   └── fake_engine.py          # deterministic test double (no model weights needed)
├── models/tts.py             # TTSRequest/TTSResponse/PreprocessRequest/PreprocessResponse/...
└── data/
    ├── dialects.py            # the 13 real dialects + MSA, sourced as described above
    ├── voice_design.py         # the real gender/pitch/age enum, read from the installed package
    └── pronunciation_overrides.json  # editable term -> Arabic-pronunciation overrides

backend/tests/
├── unit/                   # segmenter, diacritizer logic, dictionary, audio_merger, request
│                            # validation, transliterator (real espeak-ng) — all offline
├── contract/                # API behavior against FakeEngine + mocked diacritizer — offline
└── integration/              # real models, real MPS/CUDA/CPU inference — opt-in, RUN_MODEL_INTEGRATION_TESTS=1

frontend/src/
├── App.tsx                    # orchestration + state
├── components/                 # Header, TextComposer, DialectRail, VoicePanel,
│                               # ReferenceAudioUpload, GenerationControls, PreprocessPreview,
│                               # AudioPlayer, ErrorBanner, StreamingDemo
├── hooks/
│   ├── useWaveformPeaks.ts      # real waveform from decoded audio, not decorative bars
│   ├── usePreprocessPreview.ts   # debounced live "what will be spoken" preview
│   └── useStreamingSynthesis.ts   # drives /api/tts/stream, gapless Web Audio playback
└── api/client.ts                # typed fetch wrappers, incl. synthesizeSpeechStream (SSE)

scripts/
├── samples.py               # the sample matrix shared by both scripts below
├── generate_samples.py      # generates+saves real audio -> docs/SAMPLE_GALLERY.md
└── benchmark_tts.py         # real latency/TTFA measurement -> docs/PERFORMANCE_BENCHMARKS.md

docs/
├── TTS_MODEL_EVALUATION.md          # phase 2's Groq evaluation — superseded, kept as history
├── DIACRITIZATION_EVALUATION.md      # diacritizer model comparison + two reproduced defects/fixes
├── ENGLISH_TTS_EVALUATION.md          # native vs dual_model vs transliteration — measured evidence
├── SAMPLE_GALLERY.md                   # real generated audio across MSA/dialect/hard names/
│                                        # numbers-dates-currency-English-mix/style variants
├── PERFORMANCE_BENCHMARKS.md            # real measured latency + streaming TTFA, via benchmark_tts.py
├── PRODUCTION_ARCHITECTURE.md            # recommended architecture for a real-time avatar
└── audio/                              # phase 2's sample audio (superseded) + audio/samples/ (current)
specs/                                   # Spec Kit planning artifacts for phases 1 and 2
```
