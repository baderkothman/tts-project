> **Superseded.** This phase (`002-saudi-tts-prototype`) selected Groq's hosted
> `canopylabs/orpheus-arabic-saudi`. The project has since moved to a third phase that
> uses exclusively `oddadmix/lahgtna-omnivoice-v2`, run locally — no hosted provider,
> no Groq, no fallback. See the root `README.md` for the current architecture and
> `backend/app/data/dialects.py` for how dialect selection actually works today. Kept
> here as a real, dated record of why Groq was chosen at the time — not current.

# Saudi Arabic TTS: Model & API Evaluation

Every candidate below was either called live or checked directly against its own
documentation/metadata — none was dismissed on assumption (spec.md FR-014, Constitution V).
Full narrative reasoning is in `specs/002-saudi-tts-prototype/research.md` R1.

## Comparison

| Candidate | Type | Dialect authenticity | Male voice | Female voice | Voices | Python integration | Latency | Individual-dev accessible | Commercial license | Local difficulty | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Groq — Orpheus Arabic** (`canopylabs/orpheus-arabic-saudi`) | Hosted API | Vendor-documented Saudi/Gulf dialect training (not MSA) | ✅ 3 voices, live-verified | ✅ 3 voices, live-verified | 6 | Already implemented, `httpx` REST | ~460-685ms generation for 1.4-2.4s of audio (RTF 0.24-0.34), live-measured | Yes — one API key, no GPU | Groq's own API terms | None — hosted | **Selected** |
| `NAMAA-Space/NAMAA-Saudi-TTS` (HF, Chatterbox) | HF model, live-tested via its Space | Configured/prompted for Saudi dialect; not independently verified against a native-speaker panel | Bundled default voice — pitch analysis (median F0 ≈113Hz) consistent with male | ❌ not available without a reference clip this project has no right to use, or unverified self-hosting | 1 usable today | Would require `chatterbox-tts` + `torch` locally, or the public Space (unsuitable as a backend dependency) | ~6s via the shared public Space (not representative of a dedicated deployment) | Yes for the Space demo; local self-hosting untested | **MIT** | Untested MPS/Apple Silicon viability | Tested, not selected |
| `NAMAA-Space/NAMAA-Saudi-TTS-V2` (HF, F5-TTS) | HF model, card reviewed in detail | Best-documented Najdi-specific training (~18.4h curated Saudi/Najdi podcast data) | Voice-cloned per reference clip, not a fixed voice | Voice-cloned per reference clip, not a fixed voice | Unlimited via cloning, none fixed | Full voice-cloning pipeline required for every call | Not tested (disqualified on license first) | Yes technically, but every call needs a rights-cleared reference clip | **CC-BY-NC-SA-4.0 — non-commercial** | Reference-audio sourcing + local F5-TTS inference | Reviewed, not selected |
| `AhmedEladl/Magpie-TTS-Saudi-Arabic` (HF, NeMo) | HF model, card reviewed in detail | Fine-tuned specifically on a female Saudi speech dataset; base-vs-finetuned samples included in the repo | ❌ not offered by this specific checkpoint | ✅ dedicated female Saudi voice (by dataset name and filename) | 1 (female) | Documented inference path is `.cuda()`-only, `nemo_toolkit[all]` (heavy) | Not tested (dependency cost) | Partial — heavy install | Not stated in the fetched card | CUDA-oriented, no confirmed CPU/MPS path | Reviewed, not selected |
| ElevenLabs | Hosted API, already integrated | **Checked live**: this account's `GET /v1/voices` returns 21 voices, all English-language, American/British-accented — zero Saudi or Arabic-labeled | ❌ no Saudi voice in this account | ❌ no Saudi voice in this account | 0 genuinely Saudi | Already integrated from a prior feature | N/A | Yes, already have a key | Commercial (paid plan) | None — hosted | Checked live, not selected |
| OpenAI / Gemini TTS | Hosted API | Not tested — neither publishes a documented Saudi-dialect training claim the way Groq does | Untested | Untested | Untested | Not integrated | Not measured | Presumably yes | Commercial | None — hosted | **Not tested** (disclosed, not claimed inferior) |
| Microsoft Edge Neural TTS (`ar-SA`) | Hosted, credential-free | **Already established false** in the prior feature's own live testing — MSA-trained, not Saudi-dialect-trained | N/A | N/A | N/A | Already implemented (prior feature) | Already measured (prior feature) | Yes, zero config | Free | None — hosted | Excluded by prior evidence, not re-tested |

## Why Groq, in one paragraph

Groq's Orpheus Arabic model is the only candidate that is simultaneously: genuinely
dialect-trained (not MSA or generic Arabic), offers real male **and** female voices without
needing a reference-audio clip this project has no right to use, requires no GPU or local
model management, and was live-tested end to end with real latency numbers before this
decision was written down. Every Hugging Face alternative found is either missing a second
gender cleanly, license-disqualified, or dependency-heavy in a way that contradicts this
phase's explicit "keep it simple" mandate. None was dismissed without being called or its
documentation directly checked.

## Real measured latency (Groq, this session)

Three repeated calls, same text, same voice (Abdullah), no warm-up discarded:

| Run | Generation time | Audio duration | Real-time factor |
|---|---|---|---|
| 1 | 592.9ms | 2399.8ms | 0.247 |
| 2 | 684.5ms | 2399.8ms | 0.285 |
| 3 | 569.8ms | 2399.8ms | 0.237 |

Real-time factor consistently well under 1.0 — generation is faster than the resulting
audio's own playback duration, a reasonable signal for eventual real-time use, though this
prototype does not stream and this is not a formal benchmark harness (that apparatus was
explicitly removed as out of scope for this phase, per spec.md FR-012).

Real sample audio: `docs/audio/saudi-male-sample.wav`, `docs/audio/saudi-female-sample.wav`
(both genuinely generated during this evaluation, not placeholders).

## A real bug found and fixed during this evaluation

Groq's WAV response declares both its RIFF and `data` chunk sizes as `0xFFFFFFFF` — an
ffmpeg/libavformat streaming-header convention (visible in the response's own `Lavf61.7`
muxer tag) meaning "size unknown at write time." Python's `wave` module reads this
literally, producing a nonsensical multi-hour duration for a 1-2 second clip. Fixed in
`backend/app/services/latency.py::wav_duration_ms` by computing the frame count from the
actual bytes present in the `data` subchunk rather than trusting a declared size that can
exceed it — confirmed with a regression test reproducing the exact corrupted header.

## Honesty note on dialect-authenticity scoring

No native Saudi-speaker rating panel was available in this environment. "Dialect
authenticity" above is stated at the confidence each source actually supports: Groq's is a
vendor documentation claim (not independently re-verified by ear in this session, though
real audio was generated and is available to listen to); NAMAA-Saudi-TTS's male-leaning
pitch estimate is a real but limited technical signal (fundamental frequency alone does not
prove dialect authenticity, only a plausible gender). No score above claims more certainty
than its evidence supports.
