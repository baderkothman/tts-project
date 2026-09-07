# Phase 0 Research: Saudi Arabic TTS Prototype

All decisions below trace to a real, executed probe made earlier in this session — a
live API call, a live Hugging Face Space call, or a direct `GET` against a provider's own
metadata endpoint — not to vendor marketing copy alone (Constitution V).

## R1. Which TTS solution for Saudi Arabic?

**Decision**: **Groq's `canopylabs/orpheus-arabic-saudi`**, already integrated in this
repository from the prior feature (`001-arabic-tts-prototype/backend/app/providers/
groq.py`), carried forward as this feature's sole provider.

**Rationale**: Of every candidate actually tested (not just read about), this is the only
one that clears every one of the brief's "Critical"/"High" criteria simultaneously:

| Criterion | Groq Orpheus Arabic |
|---|---|
| Saudi dialect authenticity | Vendor-documented as trained on colloquial Saudi/Gulf speech, not MSA |
| Male voice quality | 3 voices (Abdullah, Fahad, Sultan) — real, live-tested in 001 |
| Female voice quality | 3 voices (Lulwa, Noura, Aisha) — real, live-tested in 001 |
| Number of usable voices | 6, evenly split by gender — no fabricated voices needed |
| Python integration | Already implemented, tested, and live-verified (httpx REST call) |
| Latency | Measured in 001: real per-call figures, plus a documented rate-limit-driven TTFA climb under load |
| Individual developer accessibility | One API key, no GPU, no local model management |
| Commercial-use license | Groq's own API terms — no separate model license to track |
| Local execution difficulty | N/A — hosted |

**Alternatives considered** (each tested or checked live, not dismissed on assumption):

### A. `NAMAA-Space/NAMAA-Saudi-TTS` (Hugging Face)

Chatterbox Multilingual TTS fine-tune, **MIT license** (permissive), 536M params, 50 likes
— the highest community-trust signal of any Saudi-specific Hugging Face model found.

Live-tested via its own Hugging Face Space (`omarelshehy/NAMAA-Saudi-Voice`) using
`gradio_client`, not merely read about: called `/generate_tts_audio` with a real Saudi
sentence ("وش رايك نطلع نتعشى اليوم؟"), got real audio back in ~6 seconds
(`docs/audio/namaa-saudi-sample1.wav` in the prior feature's audio directory). A pure-numpy
autocorrelation-based pitch estimate of the output (median F0 ≈113Hz, mean ≈122Hz) falls in
the typical adult male range (~85-180Hz), not the typical female range (~165-255Hz) —
consistent with (not a certain proof of) the bundled default reference voice being male.

**Why not selected**: the model's one bundled default voice gives exactly one gender for
free. A second (female) voice requires either:
- A reference audio clip this project has no documented right to use (the brief explicitly
  prohibits using reference audio without confirmed rights), or
- Self-hosting the model locally with `chatterbox-tts` + `torch`, whose Apple Silicon/MPS
  viability was not verified in this session (the public Space runs on a shared/pooled GPU
  not under this project's control, unsuitable as a production backend dependency anyway).

Genuinely a strong candidate for a **future** iteration if a rights-cleared female Saudi
reference clip is sourced, or if self-hosting is later justified — recorded here as a real
comparison point, not a dismissed one.

### B. `NAMAA-Space/NAMAA-Saudi-TTS-V2` (Hugging Face)

F5-TTS (flow-matching Diffusion Transformer) fine-tune, full fine-tune (not LoRA) from
`SWivid/Habibi-TTS`'s Saudi-specialized checkpoint, trained on ~18.4 hours of Najdi/Saudi
podcast speech across five curated datasets — the most Saudi-specific *training data* of
any candidate found, and the model card itself documents the architecture, hyperparameters,
and reference-clip guidelines in detail.

**Why not selected**: two disqualifying properties, both real, both checked directly on the
model card:
- **License: CC-BY-NC-SA-4.0** (non-commercial, inherited from the base Habibi-TTS model)
  — fails the brief's own "commercial-use license: High importance" criterion outright.
- **Requires a fresh reference audio clip for every single generation** (genuine
  voice-cloning, not a fixed-voice model) — a materially heavier integration than a
  fixed-voice API call, and the brief explicitly says "do not turn this phase into a full
  voice-cloning system."

### C. `AhmedEladl/Magpie-TTS-Saudi-Arabic` (Hugging Face)

NVIDIA Magpie TTS (357M) fine-tuned specifically on a female Saudi speech dataset
(`AhmedEladl/saudi-voice-dataset`) — the filename (`Magpie-TTS-Saudi-Female.nemo`) and the
training dataset name both confirm this is a genuine, dedicated **female** Saudi voice, with
real base-vs-fine-tuned comparison audio samples included directly in the repository.

**Why not selected**: the documented inference path calls `.cuda()` with no CPU/MPS
fallback shown, and requires `nemo_toolkit[all]` — a substantially heavier dependency than
this phase's "keep it simple" mandate justifies for a single voice. License was not stated
in the fetched model card. A real candidate for a future female-voice addition once a
CPU/MPS-viable inference path is confirmed.

### D. ElevenLabs

Already integrated in the prior feature, with an active API key. Queried this account's own
voice library live (`GET /v1/voices`, 21 voices returned) — **zero** are Saudi-labeled or
even Arabic-labeled; every voice is English-language with an American or British accent
label. ElevenLabs' documented "Saudi Arabic" support (cited in the brief) is a general
multilingual-model *locale* capability applied to any of these English voices, not a
dedicated Saudi-accented voice — matching this project's own prior finding
(`001-arabic-tts-prototype/docs/DIALECT_EVALUATION.md`).

**Why not selected**: no evidence of genuine Saudi dialect authenticity exists for this
account's voices; adopting it would mean asserting a dialect claim this project cannot back
with a citation or an observation (Constitution V forbids this).

### E. OpenAI / Gemini TTS

Not independently live-tested in this session (time-boxed against the brief's "do not
create a massive provider study" instruction, given Groq already cleared every criterion
with live evidence and neither OpenAI nor Gemini publish a documented Saudi-dialect
training claim the way Groq's Orpheus Arabic model does). Recorded here as **not tested**,
not as **rejected on quality grounds** — an honest distinction this project's Constitution V
requires.

### F. Microsoft Edge Neural TTS (`ar-SA`)

Not re-tested. Already live-tested in the prior feature and confirmed MSA-trained, not
Saudi-dialect-trained (`001-arabic-tts-prototype/docs/DIALECT_EVALUATION.md`) — fails
FR-001 by this project's own existing evidence, so re-testing it would not change the
conclusion.

## R2. What changes in the reused Groq adapter, if anything?

**Decision**: None. `providers/groq.py` from 001 (200-char word-boundary-safe chunking,
WAV stitching via the `wave` module, 401/429/5xx error mapping, one bounded
`Retry-After`-honoring retry on 429) is copied forward unchanged in logic — every finding
that shaped it (the lowercase-voice-id requirement, the 10 req/min rate limit) is still
true of the same vendor endpoint.

**Rationale**: Constitution VIII — don't rewrite working, already-tested code. The `Voice`
model this feature exposes is narrower than 001's `VoiceConfig` (no `locale`,
`supports_ssml`, `supports_emotions` fields this feature has no use for), so the adapter's
`get_voices()` return type changes, but its actual synthesis logic does not.

## R3. Latency measurement scope

**Decision**: Three `perf_counter` marks — request received, provider call started, audio
fully received — rather than 001's full T0-T7 streaming trace.

**Rationale**: FR-007 requires generation time, audio duration, and real-time factor;
nothing in spec.md requires time-to-first-audio or a streaming path (Groq's adapter has no
real incremental streaming to measure anyway — confirmed absent in 001). Building the fuller
trace apparatus for a value spec.md doesn't ask for would violate Constitution VIII.

## Resolved Technical Context

| Unknown | Resolution |
|---|---|
| Language/Version | Python 3.12 |
| Primary dependencies | FastAPI, Uvicorn, Pydantic v2, httpx, pytest, pytest-asyncio |
| Storage | None |
| Testing | pytest + pytest-asyncio; offline by default, one integration test credential-gated |
| Target platform | Local machine, macOS/Linux, Python 3.12+ |
| Project type | Web service (Python backend) + one static page |
| Constraints | Requires `GROQ_API_KEY` (this phase has no credential-free path, unlike 001) |
| Scale/scope | Single concurrent user, prototype |
