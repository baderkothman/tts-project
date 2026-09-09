# لهجتنا — Arabic Dialect Text-to-Speech

Type Arabic text — Modern Standard or one of 9 real dialects, optionally mixed with
English — pick a voice by attribute (gender, pitch) or clone one from a short
reference clip, and hear it spoken with automatic diacritization and natural-sounding
embedded English. Speech synthesis itself is powered **exclusively** by
[`oddadmix/lahgtna-omnivoice-v2`](https://huggingface.co/oddadmix/lahgtna-omnivoice-v2)
(the [OmniVoice](https://github.com/k2-fsa/OmniVoice) architecture), run locally through a
Python inference service. No Groq, ElevenLabs, Azure, Gemini, or any other hosted TTS
provider ever generates audio — and no fallback to one. (Kokoro-82M, also local and
open-source, is used only as a selectable *alternative* for English words — see
[Mixed Arabic/English speech](#mixed-arabicenglish-speech) below.)

The one deliberate exception: an **automatic** AI dialect rewrite step sends the typed
text (never audio) to OpenAI to rewrite it into the chosen dialect's wording — and fully
diacritize it — right before synthesis, whenever the server has `OPENAI_API_KEY` set.
There is no per-request toggle: it's just part of what "generate speech" does, triggered
once per generate click, never while typing or picking a dialect. Unset the key and it's
silently skipped — the rest of the app works identically without it. See
[AI dialect rewrite (automatic, OpenAI)](#ai-dialect-rewrite-automatic-openai) below.

This is the third phase of this repository's Arabic TTS work. The first two phases
(`specs/001-arabic-tts-prototype/`, `specs/002-saudi-tts-prototype/`) used hosted vendor
APIs (Edge, Groq, ElevenLabs); all of that code has been removed. See
`docs/TTS_MODEL_EVALUATION.md` for the (now superseded) reasoning behind phase 2's Groq
pick, kept as a historical record.

## Requires credentials?

**No, for speech synthesis.** Both TTS models download anonymously from Hugging Face Hub
on first run (Lahgtna ~2.4GB, the diacritizer ~1.2GB, cached under `.hf_cache/` after that;
Kokoro-82M is much smaller). `HF_TOKEN` in `.env.example` is optional — it only raises the
Hub's anonymous download rate limit, nothing else needs it. One system dependency:
`espeak-ng` (`brew install espeak-ng` / `apt install espeak-ng`), needed for Kokoro's
phonemizer and for the English-transliteration fallback — see below.

**Yes, for the automatic AI dialect rewrite step only** — `OPENAI_API_KEY` in `.env`. Leave
it unset and it's simply reported unavailable (`/api/model-info`'s
`dialect_rewriter_configured: false`) and silently skipped at generation time; every other
feature works unchanged.

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
   gender (`male`/`female`) and pitch. Passing anything outside that vocabulary raises an
   error inside the package itself — this app's UI only exposes what is actually in that
   enum. Two categories the package's vocabulary also supports are deliberately not exposed:
   - `age` ("child"/"teenager"/"young adult"/"middle-aged"/"elderly") — a controlled test
     against this exact fine-tuned checkpoint (5 real generations per category, F0 measured
     directly, ANOVA + pairwise t-tests) found the 3 middle categories statistically
     indistinguishable from each other (p=0.36-0.56) — see
     `backend/app/data/voice_design.py`'s module docstring for the full numbers. Rather than
     ship a control that mostly does nothing, no age instruct is ever sent.
   - `whisper` style — removed from the UI/API for scope, not a measured defect like age
     above; the package itself still accepts it as an instruct value.
2. **Voice cloning** — a 3–10s reference audio clip (+ optional transcript, auto-transcribed
   via Whisper if omitted).
3. **Auto** — the model picks a voice with no guidance.

**There is no tone/emotion instruct** — checked directly against the installed package
source (`omnivoice.utils.voice_design._INSTRUCT_CATEGORIES`), not assumed: the entire closed
vocabulary is gender, age, pitch, whisper, an English-only accent list, and a Mandarin-only
regional-dialect list. None of those categories is "happy"/"sad"/"expressive" or any other
tone control, and inventing one to expose in the UI would violate the "no invented
capabilities" rule this whole section is named after. The one real, measured lever for
perceived flatness turned out to be a generation parameter, not an instruct keyword:
`class_temperature` (token-sampling temperature for the diffusion audio head) defaults to
`0.0` in the package — fully greedy, deterministic decoding — and was never overridden here
until now. A direct controlled comparison against this exact checkpoint (same text/instruct,
4 real generations per condition, F0 measured via `librosa.pyin`) found `class_temperature=0.7`
raised mean F0 standard deviation from ~26.5 Hz to ~43.6 Hz (+~65% relative, i.e. less
monotone) — real and directionally consistent, though with only 4 reps per condition it
didn't reach significance (Welch t-test p=0.107). `services/inference.py` now sends
`class_temperature=0.6` by default (a moderate pick given that uncertainty) instead of the
package's own `0.0`; intelligibility at this setting wasn't separately re-measured (only
prosodic variation was), so treat it as a reasoned default worth revisiting with more data,
not a settled result.

**Dialect is a separate parameter** (`language`), not part of the voice-design instruct
string (an earlier assumption during this project that dialect would be an instruct
keyword was wrong — verified by reading the package's own instruct validator, which
rejects anything not in that gender/pitch/age/whisper/accent list). `backend/app/data/dialects.py`
maps 9 of the 13 dialects `oddadmix/lahgtna-omnivoice-v2`'s own model card marks
**completed** (not the six it marks merely *planned* — those are never exposed) to the
real ISO-ish language code the installed package's language resolver accepts, plus MSA.

The other 4 — **Palestinian, Lebanese, Syrian, and Yemeni** — were shipped briefly and then
removed after real user feedback that they don't work: Palestinian/Lebanese/Syrian shared one
underlying code (`apc`, Levantine Arabic) with no distinct parameter to tell them apart, and
Yemeni has no language code in the installed package at all — selecting it silently fell back
to language-agnostic mode. Rather than keep 4 dialect options that produce no real dialect
conditioning, they were removed outright; see `data/dialects.py`'s module docstring and
`REMOVED_UNRELIABLE_DIALECTS` for the full record.

`GET /api/voices` reflects this honestly too — it returns the real gender/pitch
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

## AI dialect rewrite (automatic, OpenAI)

Everything above only *conditions pronunciation* — it never changes the words the user
typed. There is no local model in this app that rewrites an MSA-ish sentence into another
dialect's actual vocabulary/phrasing; the user has always had to type dialectal Arabic
themselves for that to come through.

`services/dialect_rewriter.py` fills that gap — **automatically, not as a toggle**: every
`POST /api/tts` (and avatar generation) call sends the typed text and chosen dialect to
OpenAI (`gpt-5-mini` by default, `OPENAI_MODEL` overridable, `reasoning: "low"` — see the
module docstring for why "minimal" was tried and rejected: faster but measurably
unreliable, real garbled/doubled output sampled directly against the live API) and gets
back the sentence rewritten in that dialect's real wording, fully diacritized for how it's
actually spoken (no MSA case endings on dialectal words — the same rule the local
diacritizer enforces) — gated only on whether `OPENAI_API_KEY` is set server-side
(`dialect_rewriter.is_configured()`), never on a per-request field. Unset the key and it's
silently skipped, exactly like before; nothing else changes. That output is then used as-is;
the local Fine-Tashkeel diacritizer already refuses to re-diacritize text that already
carries diacritics (see above), so no special-case bypass was needed to satisfy "use the AI
output as-is."

**Deliberately never triggered by typing or picking a dialect.** `POST /api/preprocess` —
the live "what will be spoken" preview that fires on every debounced keystroke/dialect
change — never calls this at all; it only runs the local, free diacritizer. Calling a paid
external API on every keystroke would be real, unnecessary cost for no benefit the user asked
for, so the rewrite is scoped to actual generation requests, triggered exactly once per
"generate" click. The preview can therefore show slightly different wording than what
actually gets spoken; the real response's `processed_text`/`segments` (surfaced right after
generation) are authoritative for what was actually said — see `App.tsx`'s `handleGenerate`,
which overwrites the preview panel with those the moment audio is ready.

**The prompt's own diacritics instructions are not trusted as sufficient on their own** —
real, reproduced live-API sampling found the model sometimes left a word completely
undiacritized while the rest of the sentence was fully vocalized, and sometimes let a
classical MSA case ending (i'rab) slip through for a dialect that shouldn't have one (e.g. a
Bahraini rewrite with a stray `ُ`/`ِ` case ending intact). Two backstops now sit between the
model's output and TTS, in `dialect_rewriter._sanitize`:

- **A deterministic case-ending strip** (`diacritizer.strip_dialectal_case_endings` — the
  exact same rule the local, non-AI diacritization path already enforces) runs on every
  non-MSA rewrite regardless of what the model did, so a missed "no i'rab" instruction can't
  reach TTS.
- **A completeness check** rejects a rewrite that leaves any real (3+ letter) Arabic word
  with zero diacritic marks, and `rewrite()` retries the API call once automatically before
  giving up — a sporadic generation glitch, not something a deterministic rule can repair
  after the fact (there's no diacritic to insert for a whole bare word from the outside).

The same call also fixes **speaker-gender agreement** when a voice gender is chosen
(`voice_design` mode, male/female — not "auto" or `clone`, which have no gender to agree
with): Arabic predicate adjectives and participles that describe the *speaker referring to
themselves* ("أنا سعيد" vs "أنا سعيدة") are conjugated to match the chosen voice, regardless
of which form the user actually typed. This is scoped narrowly on purpose — a second-person
addressee or a third person the sentence talks about keeps whatever gender the text already
gives them; only self-reference follows the voice. (Real rule-based Arabic morphology for
this is genuinely hard to get right — the same reasoning that put dialect rewriting itself
behind a model instead of a dictionary.)

**Embedded English is left exactly as typed** — never translated, and never transliterated
into Arabic script. An earlier iteration of this prompt *did* convert embedded English into
Arabic-script phonetic spelling (e.g. "meeting" → "ميتنج"); direct user feedback reversed
that decision, so the current prompt explicitly instructs the model to leave any Latin-script
word untouched, and only rewrite/diacritize the surrounding Arabic. This also matches the one
already-existing behavior for mixed-language text everywhere else in the app — `native`
pipeline mode (below) already leaves English segments as-is.

- **Automatic when configured, never per-request** — no request field turns this on or off;
  it's decided once, server-side, by whether `OPENAI_API_KEY` is set. No surprise cost swing
  between otherwise-identical requests, and one less setting for the user to think about —
  the flow is just text → dialect → generate.
- **Never triggered by typing or a dialect change** — see above; only an actual "generate"
  click (`POST /api/tts`, `POST /api/tts/stream`, or an avatar generation) can call OpenAI.
- **Disclosed, not hidden** — the response's own `warnings` array says the text was
  rewritten via OpenAI (shown in the "ready to speak" preview panel after generation); the
  footer names this as the one exception to the local-only claim above.
- **Fails loudly, not silently** — if `OPENAI_API_KEY` is set but the call itself fails,
  `/api/tts` returns an error (502) instead of quietly falling back to unrewritten text.
  Unset entirely, it's a clean, silent skip — not an error.
- **Validated directly against the live API while building this**, not just mocked: the
  dialect rewrite, the gender-agreement scoping (self vs. addressee vs. third person, across
  MSA/Saudi/Egyptian, both voice genders), the case-ending backstop, and the completeness
  retry were all sampled against the real endpoint — see git history for the specific cases.
  Broader native-speaker dialect-authenticity evaluation the way diacritization got
  (`docs/DIACRITIZATION_EVALUATION.md`) hasn't been done.

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

## Talking Avatar (experimental)

A second feature, built on top of the TTS pipeline above without modifying it: upload a
portrait, type Arabic text, pick a dialect/voice/emotion, and get back an MP4 of the
portrait animated to the generated speech. Real end to end — real Lahgtna-generated
audio, a real generated video, an async job API with live progress
(`GET /api/tts/avatar/jobs/{id}/events`, Server-Sent Events) instead of one long-held HTTP
request.

**Real AI lip sync is active by default when `REPLICATE_API_TOKEN` is set** — SadTalker,
run via [Replicate](https://replicate.com)'s hosted API (`ReplicateAvatarEngine`; every
open-source lip-sync model evaluated needs CUDA, which this repo's dev/deploy hardware
doesn't have — see the evaluation doc). Real, metered cost per generation
(~$0.09–0.15, confirmed against actual billed predictions), so it's opt-in via that one
credential. Unset, the app falls back automatically to `StubAvatarEngine` — a free,
non-AI placeholder (audio-reactive idle motion, no real lip sync) so the feature still
works end to end with zero cost and zero external dependency. See:

- `docs/AVATAR_MODEL_EVALUATION.md` — the model comparison and why
- `docs/AVATAR_ARCHITECTURE.md` — the `AvatarEngine` abstraction, job state machine,
  storage/caching/security, and the concrete plan for a real GPU-backed engine later
- `docs/AVATAR_SETUP.md` — running it (one extra system dependency: `ffmpeg`)

## API

```text
GET  /api/health        status, whether Lahgtna finished loading, device
GET  /api/model-info    repo id, architecture, device, sample rate, capabilities, pipeline modes,
                         diacritizer/English-TTS load status, dialect_rewriter_configured
GET  /api/dialects      the 9 real dialects + MSA
GET  /api/voices        gender/pitch options (no named-voice roster — see above)
POST /api/preprocess    JSON: text + dialect_id + pipeline_mode -> processed text + per-segment
                         breakdown, no audio, no AI dialect rewrite (local-only — the UI's live
                         preview; see "AI dialect rewrite" above for why it's excluded here)
POST /api/tts           multipart/form-data: text + mode + pipeline_mode + dialect/voice options
                         [+ ref_audio file] -> audio + the same processed-text/segments
                         breakdown (the AI dialect rewrite runs automatically here, in
                         addition to preprocessing, whenever OPENAI_API_KEY is set)
POST /api/tts/stream    same request shape as /api/tts -> Server-Sent Events, one `chunk` per
                         sentence as its audio is ready, then a `done` event with real measured
                         time-to-first-audio (`ttfa_ms`) — see "Streaming and latency" below

GET  /api/tts/avatar/emotions           the 6 real emotion presets — see "Talking Avatar" above
POST /api/tts/avatar                    multipart/form-data: text + dialect/voice options +
                                          emotion + portrait image -> 202 + {job_id} (same
                                          automatic AI dialect rewrite as /api/tts, no field
                                          needed to enable it)
GET  /api/tts/avatar/jobs/{id}          job status/progress + video_url/audio_url once ready
GET  /api/tts/avatar/jobs/{id}/events   Server-Sent Events progress stream (terminates on
                                          completed/failed/cancelled)
POST /api/tts/avatar/jobs/{id}/cancel   cancels a queued job outright; a running job's result
                                          is discarded once its current stage finishes (see
                                          docs/AVATAR_ARCHITECTURE.md's "Cancellation" section)
GET  /api/tts/avatar/jobs/{id}/video    the generated MP4
GET  /api/tts/avatar/jobs/{id}/audio    the generated WAV (same audio muxed into the video)
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

## Deploying

`Dockerfile` + `railway.json` at the repo root — see `DEPLOY.md` for the full
Railway setup (a persistent Volume for the model cache, why CPU-only `torch`
matters, and what was actually verified locally before this was written).
Not Vercel: this backend keeps a ~3.6GB model warm in memory on a long-lived
process, which is a different shape than Vercel's stateless Functions
support — `docs/PRODUCTION_ARCHITECTURE.md` covers the same "not a typical
web app" reasoning in more depth.

## Setup

```bash
brew install espeak-ng   # or: apt install espeak-ng — needed by Kokoro + the transliteration fallback
brew install ffmpeg      # or: apt install ffmpeg — needed by the Talking Avatar feature only
                          # (see "Talking Avatar" above / docs/AVATAR_SETUP.md); everything else
                          # in this app works without it
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env   # optional — no credentials required, except OPENAI_API_KEY for the
                        # automatic AI dialect rewrite step (see above)

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
.venv/bin/pytest backend/tests -v -m "not integration"   # offline, no model weights: 194 pass
.venv/bin/pytest backend/tests                              # + the real-ffmpeg avatar test: 197 pass
RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
                                                            # + real Lahgtna weights, real MPS inference

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
├── api/
│   ├── tts.py                # /api/health, /api/model-info, /api/dialects, /api/voices,
│   │                          # /api/preprocess, /api/tts
│   └── avatar.py              # /api/tts/avatar and the job endpoints — see "Talking Avatar" above
├── services/
│   ├── inference.py          # TTSEngine — the one OmniVoice (Arabic) instance, loaded once
│   ├── english_tts.py         # Kokoro-82M wrapper, for dual_model mode
│   ├── diacritizer.py         # Fine-Tashkeel wrapper — see docs/DIACRITIZATION_EVALUATION.md
│   ├── dialect_rewriter.py    # automatic OpenAI dialect rewrite — see "AI dialect rewrite" above
│   ├── language_segmenter.py  # pure Unicode-script Arabic/English segmentation, no model
│   ├── transliterator.py      # espeak-ng-driven phonetic EN->Arabic-script fallback
│   ├── pronunciation_dictionary.py  # JSON-backed term overrides, applied before segmentation
│   ├── audio_merger.py        # loudness/rate-matching + crossfade stitching for dual_model
│   ├── sentence_splitter.py   # splits processed text into sentence chunks for /api/tts/stream
│   ├── text_preprocessor.py   # orchestrates all of the above into one pronunciation-ready pass
│   ├── speech_pipeline.py     # orchestrates text_preprocessor + engines into final audio,
│   │                          # incl. synthesize_stream() for sentence-chunked streaming
│   ├── audio.py                # np.ndarray <-> WAV bytes, duration
│   ├── fake_engine.py          # deterministic TTS test double (no model weights needed)
│   ├── portrait_validator.py    # Talking Avatar: face/format/size validation on upload
│   ├── avatar_engine.py          # Talking Avatar: the AvatarEngine ABC + EmotionConfig
│   ├── avatar_jobs.py             # Talking Avatar: the async job manager/state machine
│   ├── tts_cache.py                # Talking Avatar: content-addressed TTS audio cache
│   └── avatar_engines/               # replicate_engine.py (real AI lip sync, active when
│                                      # REPLICATE_API_TOKEN is set), stub_engine.py (free
│                                      # fallback), hf_jobs_engine.py (alternative, planned),
│                                      # fake_engine.py (test double) — see docs/AVATAR_ARCHITECTURE.md
├── models/
│   ├── tts.py                 # TTSRequest/TTSResponse/PreprocessRequest/PreprocessResponse/...
│   └── avatar.py                # AvatarGenerationRequest/AvatarJobResponse/AvatarJobStatus/...
└── data/
    ├── dialects.py            # the 9 real dialects + MSA, sourced as described above
    ├── voice_design.py         # the real gender/pitch/age enum, read from the installed package
    ├── emotions.py               # the 6 Talking Avatar emotion presets (model-agnostic)
    └── pronunciation_overrides.json  # editable term -> Arabic-pronunciation overrides

backend/tests/
├── unit/                   # segmenter, diacritizer logic, dictionary, audio_merger, request
│                            # validation, transliterator (real espeak-ng), avatar job manager/
│                            # portrait validator/emotions/cache — all offline
├── contract/                # API behavior against FakeEngine(s) + mocked diacritizer — offline,
│                             # incl. test_api_avatar.py
└── integration/              # real models (real MPS/CUDA/CPU inference, opt-in via
                                # RUN_MODEL_INTEGRATION_TESTS=1) + the one real-ffmpeg avatar test
                                # (runs by default — see docs/AVATAR_SETUP.md)

frontend/src/
├── App.tsx                    # orchestration + state, incl. the TTS/Talking-Avatar tab switch
├── components/                 # Header, TextComposer, DialectRail, VoicePanel,
│                               # ReferenceAudioUpload, GenerationControls, PreprocessPreview,
│                               # AudioPlayer, ErrorBanner, StreamingDemo
│   ├── avatar/                  # Bayan — the app's avatar/mascot component (unrelated feature,
│   │                             # see docs/brand/avatar/AVATAR.md)
│   └── avatar-studio/            # Talking Avatar feature UI: AvatarStudioPanel, PortraitUpload,
│                                  # AvatarJobProgress, AvatarVideoResult
├── hooks/
│   ├── useWaveformPeaks.ts      # real waveform from decoded audio, not decorative bars
│   ├── usePreprocessPreview.ts   # debounced live "what will be spoken" preview
│   ├── useStreamingSynthesis.ts   # drives /api/tts/stream, gapless Web Audio playback
│   └── useAvatarJob.ts             # drives POST /api/tts/avatar + its SSE progress stream
└── api/
    ├── client.ts                 # typed fetch wrappers, incl. synthesizeSpeechStream (SSE)
    └── avatarClient.ts             # Talking Avatar: job create/get/cancel + SSE subscribe

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
├── PRODUCTION_ARCHITECTURE.md            # recommended architecture for a real-time conversational avatar
├── AVATAR_MODEL_EVALUATION.md              # Talking Avatar: model comparison + hardware-driven selection
├── AVATAR_ARCHITECTURE.md                   # Talking Avatar: AvatarEngine abstraction, job state machine,
│                                              # storage/caching/security, open questions
├── AVATAR_SETUP.md                            # Talking Avatar: running it, env vars, testing, extending
├── brand/avatar/AVATAR.md                       # Bayan (the app's mascot) — unrelated to Talking Avatar
└── audio/                              # phase 2's sample audio (superseded) + audio/samples/ (current)
specs/                                   # Spec Kit planning artifacts for phases 1 and 2
```
