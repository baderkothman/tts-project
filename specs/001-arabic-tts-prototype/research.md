# Phase 0 Research: Arabic Text-to-Speech Prototype

**Date**: 2026-09-07 | **Feature**: `001-arabic-tts-prototype`

All Technical Context unknowns are resolved below. Evidence is either cited vendor
documentation or a locally executed probe; raw capture is in `docs/PROVIDER_RESEARCH_NOTES.md`.
Per Constitution Principle V (Measured, Not Claimed), each capability claim names its source.

---

## R1. Which providers, and which one is the verified path?

**Excluded by mandate**: **Azure AI Speech is out of scope for this project entirely** —
not evaluated as a candidate, not used as a fallback, not recommended in the architecture.
This is a hard constraint from the project brief (individual developer, no Azure
company/tenant), not a quality judgment; Azure would in fact score well on several
criteria (see the one-line mention in `docs/PROVIDER_RESEARCH_NOTES.md`), which is exactly
why it needs stating as excluded-by-policy rather than excluded-by-evidence.

**Decision**: Three adapters — `edge` (Microsoft Edge Neural TTS, credential-free),
`groq` (Groq Orpheus Arabic — Saudi dialect, credential-gated), `elevenlabs`
(credential-gated). `edge` is the default and the path verified end-to-end.

**Rationale**: The target environment has no TTS credentials. A prototype whose only paths
require paid keys cannot be executed, benchmarked, or shown to have a *genuinely observed*
pronunciation defect — and FR-019 and Principle V both forbid asserting an unobserved one.
A locally executed probe confirmed `edge` returns 32 Arabic voices across 16 Arabic locales
with real chunked streaming (41 chunks, 29,376 bytes, cold TTFA 2485 ms). That makes the
full pipeline — streaming, routing, benchmarking, pronunciation demo — actually runnable.
`groq` was chosen over OpenAI's and Gemini's TTS as the second adapter specifically because
neither OpenAI nor Gemini publishes an Arabic-*dialect* voice — both are generic
multilingual voices with Arabic as one of many auto-detected input languages (confirmed
against their docs, fetched 2026-09-07) — whereas Groq documents
`canopylabs/orpheus-arabic-saudi` as a model trained specifically on colloquial Saudi/Gulf
speech, which is the actual product gap this project targets (see R2). Groq and ElevenLabs
adapters are implemented to satisfy provider independence and to be live the moment a key
is present.

**Alternatives considered**:

- *OpenAI TTS as the second adapter*: rejected — no Arabic-specific voice; the six stock
  voices (alloy, echo, fable, onyx, nova, shimmer) are English-optimized, with Arabic
  quality an unverified side effect of Whisper-family multilingual training, not a
  documented capability.
- *Gemini API TTS as the second adapter*: rejected for the same reason — Arabic (`ar`) is
  in Gemini's supported-language table and it is genuinely individual-developer accessible
  via an AI Studio key, but its 30 voices carry no dialect distinction, and Google Cloud TTS
  (the product that *does* publish Arabic voice details) is the enterprise-heavy, Azure-like
  dependency the brief separately warns against defaulting to.
- *A Hugging Face Arabic model (XTTS-v2 Arabic fine-tunes, NAMAA-Saudi-TTS,
  facebook/mms-tts-ara, F5-TTS-Arabic)*: rejected for integration, not for evaluation — see
  `docs/TTS_EVALUATION.md`'s Hugging Face section. These are self-hosted only; none offers a
  simple hosted-inference API an individual developer can call with just an API key, and
  running one requires a GPU this environment does not have.
- *Groq or ElevenLabs only*: rejected — unrunnable here, so every acceptance criterion
  would be unverifiable and the pronunciation demo would have to be invented.
- *A local neural model (Coqui/Piper/XTTS)*: rejected — heavy download, weak Arabic
  coverage, no dialect locales, and no bearing on the cloud-provider abstraction the
  feature exists to demonstrate.
- *A recorded-fixture fake only*: rejected as the primary — proves nothing about real
  streaming or latency. Retained instead as a **test** double for the offline suite.

**Honesty constraint carried into docs**: the Edge endpoint is the Microsoft Edge
read-aloud service, not a contractual API — and not Azure Speech, despite serving the same
underlying neural voice family; it needs no Azure account, tenant, or key. It has no SLA
and no published rate limits, which must be documented as suitable for prototyping only.

---

## R2. What Arabic locale and dialect coverage actually exists?

**Decision**: 16 Microsoft Arabic locales, two voices each (one female, one male).
Dialect families map to locales as: **MSA** → ar-SA; **Gulf** → ar-AE, ar-KW, ar-QA, ar-BH,
ar-OM, ar-IQ; **Egyptian** → ar-EG; **Levantine** → ar-LB, ar-SY, ar-JO; **Maghrebi** →
ar-MA, ar-DZ, ar-TN; plus ar-LY, ar-YE.

**Rationale**: Enumerated live from the voice list, and independently matching Microsoft's
published Arabic voice table. Google publishes only `ar-XA` (MSA), so it contributes no
dialect. ElevenLabs publishes no Arabic locale codes at all — its Arabic voices vary by
accent without a documented locale — so per FR-027 the ElevenLabs adapter declares an
**empty dialect set** rather than an inferred one.

**Finding that changes the design**: **No Microsoft Arabic voice (Edge) supports speaking
styles or roles.** None are Neural HD or multilingual. Emotional control for Arabic on the
Microsoft voice family therefore cannot use a `style` attribute and must be synthesized
from prosody. Groq's Orpheus Arabic model has the same limitation for a different reason —
vocal-direction tags are documented for its English model only, not the Arabic one.

**Alternatives considered**: inferring dialect from an ElevenLabs voice's marketing
description — rejected as exactly the unverified claim Principle V prohibits.

---

## R3. How is speaking style expressed when Arabic voices have no style parameter?

**Decision**: A normalized `EmotionStyle` enum in the request model, translated per adapter
through a declared capability. Edge maps style to a **prosody triple**
(rate %, pitch Hz/%, volume %). ElevenLabs maps style to its **voice settings**
(stability / similarity / style exaggeration). Groq's Arabic model accepts neither
prosody control nor style tags (research R1), so it reports the style as unsupported rather
than silently ignoring it (FR-028) — the request still succeeds, just without style
applied. Any provider that can express neither reports the style unsupported in the
response rather than ignoring it.

**Rationale**: Verified by inspection of the `edge-tts` client signature: `Communicate`
accepts exactly `rate`, `volume`, and `pitch` — no SSML, no style, no phoneme. Prosody
mapping is therefore the only native mechanism this catalogue has, and calling it "emotion"
without qualification would overstate it.

**Documented limitation**: prosody-mapped style is an *approximation* — a warm or excited
reading rendered as rate and pitch shifts, not true affective synthesis. This is stated in
the response as an `approximated` flag and in the documentation, per Principle V.

**Alternatives considered**: silently dropping unsupported styles (rejected — FR-028
forbids it); refusing the request outright (rejected — needlessly fails a usable request
when a reasonable approximation exists).

---

## R4. How should pronunciation be corrected portably?

**Decision**: Provider-independent **orthographic rewriting** is the primary mechanism —
targeted diacritization, phonetic respelling, and alias substitution applied to the text
before synthesis. SSML `<phoneme>` is implemented only as a capability-gated enhancement
for adapters declaring `supports_phoneme`.

**Rationale**: No phoneme mechanism is portable across this project's actual catalogue.
ElevenLabs restricts `<phoneme>` to English (IPA/CMU in other languages requires
eleven_v3); Groq's Orpheus Arabic model accepts no markup at all (plain `input` text only,
per its API); `edge-tts` escapes its input and accepts no markup either. **None of the
three integrated adapters declares `phoneme=True`** — a stronger finding than "phoneme is
merely secondary": with Azure excluded (R1), orthographic rewriting is not just the primary
mechanism, it is currently the *only* mechanism, because no adapter in scope exposes a
portable or even a provider-specific phoneme path. Rewriting the text works on all of them,
because every engine reads text.

**Design consequence**: `PronunciationRule` still carries optional `locale` and `provider`
scope, ready for a future SSML/phoneme-capable adapter, even though no adapter in the
current catalogue declares `phoneme=True` to use it.

**Alternatives considered**: a full automatic diacritizer (Mishkal / Farasa / CAMeL) —
rejected for now as a heavy dependency whose errors would be *harder* to debug than the
absence of diacritics; targeted rules cover the cases FR-019 actually requires. Recorded as
a future extension point rather than built.

---

## R5. Which audio format, and how does streaming reach the browser?

**Decision**: **MP3, 24 kHz mono, 48 kbit/s** default. FastAPI `StreamingResponse` forwards
each provider chunk as it arrives; the browser plays it with a plain `<audio>` element
pointed at the streaming endpoint.

**Rationale**: MP3 frames are independently decodable, so a browser begins playback on the
first frames without client-side buffering logic — which is what lets the streaming
requirement be *demonstrated* rather than merely claimed. It is also `edge-tts`'s native
output, avoiding a transcode on the measured path. Raw PCM is exposed where supported
because it is what the eventual avatar pipeline will want (no decode latency, trivially
chunkable); Opus is documented for transport efficiency.

**Alternatives considered**: WebSocket + Web Audio API scheduling — rejected as
substantially more client code for no gain at this scope, and it would put audio-assembly
logic in the frontend, violating Principle I. Recorded in the production architecture as
the right choice once barge-in and cancellation are needed.

---

## R6. Where are the latency stage boundaries?

**Decision**: Instrument T0–T7 with `time.perf_counter()`, carried on a `LatencyTrace`
object threaded through the request.

| Mark | Meaning |
|------|---------|
| T0 | Client initiates request (client-supplied, optional) |
| T1 | Server receives request |
| T2 | Text preprocessing complete |
| T3 | Provider request dispatched |
| T4 | First audio byte received from provider |
| T5 | First audio byte written to the client |
| T6 | Client can begin playback (client-reported, optional) |
| T7 | Synthesis complete |

Derived: preprocessing (T2−T1), provider TTFA (T4−T3), backend TTFA (T5−T1), total
generation (T7−T1), audio duration, and real-time factor (generation ÷ audio duration).

**Rationale**: `perf_counter` is monotonic and unaffected by clock adjustment, which
`time.time()` is not. T0 and T6 are client-side and thus optional — reporting them as
server-measured would be false precision.

**Alternatives considered**: OpenTelemetry spans — correct for production and named in the
architecture document, but it would add a dependency and a collector for a single-user
prototype, against Principle VIII.

---

## R7. How are streaming and benchmarking reconciled?

**Decision**: Benchmarks measure the **streaming** path, because TTFA is only meaningful
there. Per provider/voice/sample: one discarded warm-up call, then N measured repetitions.
Aggregate min, max, mean, median, P95 per stage. Persist per-provider JSON plus a
comparison CSV.

**Rationale**: The first call to any provider pays connection setup — the local probe
showed a cold TTFA of 2485 ms, which is connection cost, not synthesis cost. Including it
would misreport steady-state latency; discarding it silently would overstate cold-start
performance. So the warm-up is discarded *and* the fact is recorded in the results file.
P95 uses nearest-rank on small samples, since interpolated percentiles over ~5 points imply
precision that is not there.

**Alternatives considered**: measuring the non-streaming path — rejected, it cannot produce
a TTFA figure at all.

---

## R8. Async client choice

**Decision**: `edge-tts` (which uses `aiohttp` internally) for the Edge adapter; `httpx`
for the Groq and ElevenLabs REST/SSE adapters. Both are async-native.

**Rationale**: `httpx.AsyncClient.stream()` yields `aiter_bytes()`, which maps directly onto
the chunk-forwarding contract, and a single shared client enables connection reuse — the
dominant TTFA cost per R7. Mixing the two clients is acceptable because each is confined to
its adapter and never appears in domain code (Principle II).

**Alternatives considered**: reimplementing the Edge WebSocket protocol with `httpx` to use
one client everywhere — rejected as re-deriving a maintained, working protocol
implementation for cosmetic uniformity.

---

## R9. Testing without credentials

**Decision**: Default `pytest` run is fully offline. A `FakeProvider` yielding fixed bytes
covers routing, fallback, streaming, timeout, and cancellation. Live provider tests are
marked `@pytest.mark.integration` and **skip** when credentials are absent.

**Rationale**: Constitution VIII forbids live paid calls in the default suite; SC-015
requires the suite to pass without credentials, with credential tests skipped rather than
failed. A skipped test reports honestly as "not run"; a failing one would falsely signal a
defect.

**Alternatives considered**: recorded HTTP cassettes (VCR) — deferred; the FakeProvider
gives deterministic control over timeout and mid-stream failure, which replayed cassettes
do not.

---

## R10. Local hardware ceiling for on-device Hugging Face inference

**Decision**: Measured directly on the development machine rather than assumed: `sysctl -n
machdep.cpu.brand_string` → **Apple M5**; `uname -m` → **arm64**; `sysctl -n hw.memsize` →
**24 GB unified memory**; no discrete GPU, so PyTorch execution here is MPS or CPU only,
with unified memory (not a separate VRAM pool) as the real ceiling.

**Rationale**: FR-058 forbids downloading a model before its inference requirements are
checked against this environment. A model in the low hundreds of millions of parameters
(≲1B, ≲2-4 GB in fp16/bf16 or a quantized form) is comfortable; a model requiring a
dedicated multi-GB VRAM pool (most 1B+ audio-classification or TTS checkpoints documented
as "GPU recommended"/"CUDA expected") is not safely runnable locally and is routed to the
Hugging Face hosted Inference API instead, per the plan's execution-mode default.

**Alternatives considered**: assuming a generic "modern laptop" — rejected, because two of
the candidate TTS models found in R11 (1B+ parameters) would silently have been treated as
locally viable when they are not, violating Constitution V.

---

## R11. Model Evaluation Matrix — candidates for dialect TTS, diacritization, G2P, and dialect detection

Every row below was checked against a real Hugging Face model card (or its linked GitHub
repo/paper) before being recorded — none has been downloaded yet, per FR-058. "Local
viable (this machine)" applies R10's ceiling. Sources are cited per row.

### Dialect-aware and dialect-specific TTS

| Model | Task | Dialects | Speakers | Size | License | Commercial use | Local viable (24GB M5) | Notes |
|---|---|---|---|---|---|---|---|---|
| [`oddadmix/lahgtna-omnivoice-v2`](https://huggingface.co/oddadmix/lahgtna-omnivoice-v2) | Dialect TTS | Roadmap covers Egypt, Gulf states, Levant (incl. Lebanon/Syria/Palestine/Jordan), Maghreb — which are *currently* trained vs. planned is not stated on the card and must be verified by listening before any dialect claim is made | Not documented | 0.6B params (Qwen3-0.6B base) | Not stated on card | Unverified — must be confirmed before use | Yes, with headroom, if the license permits | Also ships an MLX build under `mlx-community/OmniVoice` — directly relevant to Apple Silicon local execution |
| [`ehabnegm/lahgtna-omnivoice-egyptian-v3`](https://huggingface.co/ehabnegm/lahgtna-omnivoice-egyptian-v3) | Egyptian-specific fine-tune of OmniVoice | Egyptian only | Not documented | ~0.6B (same base) | Not stated on card | Unverified | Yes | Narrower claim than v2's roadmap — lower risk of an unverified dialect claim |
| [`oddadmix/chatterbox-egyptian-v0`](https://huggingface.co/oddadmix/chatterbox-egyptian-v0) | Egyptian Arabic (Masri) TTS, fine-tuned from ResembleAI Chatterbox Multilingual | Egyptian only | Not documented | 0.5B params | **MIT** | Yes, with synthetic-audio disclosure/consent obligations | Yes | Cleanest license of the dialect-specific candidates found |
| [`facebook/mms-tts-ara`](https://huggingface.co/facebook/mms-tts-ara) | MSA baseline TTS (VITS) | MSA only ("ara" — no dialect distinction documented) | Single speaker | 36.3M params / 122 MB | **CC-BY-NC 4.0** | **No** — non-commercial only | Yes, trivially | Useful as an MSA *comparison point* in FR-054's architecture matrix, not as a production candidate given the NC license |
| [`IbrahimSalah/Arabic-F5-TTS-v2`](https://huggingface.co/IbrahimSalah/Arabic-F5-TTS-v2) / [`IbrahimSalah/F5-TTS-Arabic`](https://huggingface.co/IbrahimSalah/F5-TTS-Arabic) | F5-TTS fine-tuned for Arabic | Described as covering "regional diversity" but not broken down per dialect on the card | Not documented | Not fetched in this pass | Not fetched in this pass | Unverified | Unverified | Deferred — lower-confidence dialect claim than the two OmniVoice checkpoints; revisit only if OmniVoice underperforms in listening tests |

### Dialect detection

| Model | Input | Classes | Accuracy | Size | License | Local viable | Notes |
|---|---|---|---|---|---|---|---|
| [`IbrahimAmin/marbertv2-arabic-written-dialect-classifier`](https://huggingface.co/IbrahimAmin/marbertv2-arabic-written-dialect-classifier) | **Text** (what this feature actually needs — the user types text, there is no audio to classify before synthesis) | MSA, Gulf, Levantine, Egyptian, Maghreb (5-way) | Not published for this exact fine-tune; base MARBERTv2 dialect benchmarks report up to 92.5% (MADAR-6) | 200M params | **Apache 2.0** | Yes, CPU-viable | **Primary candidate** — matches FR-048's actual input (typed text), permissive license, small enough to run locally or via hosted API |
| [`badrex/mms-300m-arabic-dialect-identifier`](https://huggingface.co/badrex/mms-300m-arabic-dialect-identifier) | Audio | MSA, Egyptian, Gulf, Levantine, Maghrebi (5-way) | 80.73% (MADIS-5 cross-domain) | 300M params | CC BY 4.0 | Yes, CPU-viable | Not usable for this feature's text-in path; recorded for the documented future avatar pipeline (FR-046), which does classify spoken audio |
| [`tiantiaf/voxlect-arabic-dialect-mms-lid-256`](https://huggingface.co/tiantiaf/voxlect-arabic-dialect-mms-lid-256) | Audio | Egyptian, Levantine, Maghrebi, MSA, Peninsular (Gulf) | Not published on card | 1.0B params | **CC-BY-NC-4.0, explicitly "no commercial use"** | Borderline — GPU expected per card | Rejected for both this feature and the avatar pipeline: NC license and audio-only input rule it out twice over |

None of the dialect classifiers found distinguish Lebanese from broader Levantine — this
directly confirms the spec's FR-051 requirement to report the classifier's real (broader)
label plus the application's mapped preference, rather than a fabricated precise one.

### Diacritization (tashkeel)

| Model | Approach | Reported quality | Distribution | License | Local viable | Notes |
|---|---|---|---|---|---|---|
| [CATT (Character-based Arabic Tashkeel Transformer)](https://github.com/abjadai/catt), [paper](https://huggingface.co/papers/2407.03236) | Character-level transformer (Encoder-Only ~ or Encoder-Decoder, both initialized from a char-BERT pretrained on 18.5M Arabic samples) | State of the art at publication: 30.83% relative DER improvement on WikiNews, 35.21% on the CATT benchmark, and beats GPT-4-turbo by 9.36% relative DER on CATT | **Not published as a Hugging Face model repo** — checkpoints (`best_ed_mlm_ns_epoch_178.pt`, `best_eo_mlm_ns_epoch_193.pt`) are GitHub Release assets, loaded via the `catt` PyPI/GitHub package, not `transformers` | Not stated in the fetched paper page | Yes on size grounds (~50-100M params estimated), but **not usable through the hosted Inference API** since it isn't a hub model — would require a custom local-only adapter | Best quality found, but its distribution mechanism conflicts with the plan's hosted-API-first default; a local-only `local.py` backend is the only path that could use it |
| [`Abdou/arabic-tashkeel-flan-t5-small`](https://huggingface.co/Abdou/arabic-tashkeel-flan-t5-small) | FLAN-T5-small fine-tuned on tashkeel data | Not independently benchmarked against CATT in the sources found | Standard Hugging Face hub model — usable via hosted Inference API | Not fetched in this pass | Small (T5-small class, ~60-80M) | Weaker quality signal than CATT but fits the hosted-API-first default without a custom loader; candidate for the first live comparison, with CATT as a documented higher-quality local-only alternative |

### Grapheme-to-phoneme (G2P)

| Model | Coverage | Size | Distribution | License | Local viable | Notes |
|---|---|---|---|---|---|---|
| [CharsiuG2P](https://github.com/lingjzhu/CharsiuG2P) — e.g. [`charsiu/g2p_multilingual_byT5_tiny_16_layers_100`](https://huggingface.co/charsiu/g2p_multilingual_byT5_tiny_16_layers_100) | 100 languages via an ISO-639-based prefix code, Arabic included | "tiny" ByT5 variant — smallest in the family | Standard Hugging Face hub model, usable via hosted Inference API or trivially local | Not fetched in this pass | Yes, trivially (tiny model) | No dialect-specific phoneme mapping documented — MSA-oriented; a dialect-aware G2P layer, if needed, is more realistically built as rule-based post-processing on top of this than found as a single off-the-shelf model |
| [DialG2P](https://aclanthology.org/2025.arabicnlp-main.38/) | Dialectal (Egyptian-specific) end-to-end G2P: restores short vowels, maps dialect-only characters, then converts to phonemes | Research paper (ACL 2025 Arabic NLP workshop); no confirmed public Hugging Face checkpoint found in this pass | — | Unverified | Unverified | Directly relevant to the Egyptian dialect goal but not yet confirmed downloadable — recorded as a research lead to re-check, not a candidate to depend on |

**Decision**: Do not download any model yet. This table is the FR-058 gate. The
architecture comparison in FR-054/Phase 1 tasks starts with the models that are (a)
standard Hugging Face hub repos reachable through the hosted Inference API and (b)
permissively licensed for the comparison's purpose: `IbrahimAmin/marbertv2-arabic-written-
dialect-classifier` for detection, `Abdou/arabic-tashkeel-flan-t5-small` for a first
diacritization pass, `charsiu/g2p_multilingual_byT5_tiny_16_layers_100` for G2P, and
`oddadmix/chatterbox-egyptian-v0` (MIT) as the first dialect-specific TTS candidate for
Egyptian. Lebanese/Levantine and Gulf/Saudi dialect-specific TTS candidates
(`lahgtna-omnivoice-v2` variants) carry an unverified license and an unverified per-dialect
claim and MUST be confirmed on both points before being scored, not merely fetched.

**Rationale**: Constitution V and FR-058 both require relevance/license/size to be checked
*before* a download; several strong-looking candidates (voxlect, mms-tts-ara for
production use) are excluded here specifically because their license forbids the intended
use, not because they underperform — recorded so the exclusion reason stays legible.

**Alternatives considered**: fetching every candidate found and letting the listening
test decide — rejected; downloading an NC-licensed or unverified-license model before
confirming it can legally be used at all is exactly the "unnecessary download" FR-058
exists to prevent.

---

## R12. Hugging Face execution mode

**Decision**: **Hosted Hugging Face Inference API first**, for every model in R11 that is
a standard hub repo (all of them except CATT). This matches the existing credential-gated-
but-optional pattern already proven for Groq/ElevenLabs (R1) — the feature works with an
absent `HF_TOKEN`, degrading that specific capability to unavailable rather than blocking.
Local MPS/CPU execution is the fallback for models R10 confirms are comfortably small
(the diacritization T5-small, the G2P tiny ByT5, the text dialect classifier), useful when
offline or rate-limited. CATT, being local-only by distribution, is documented as a
possible local-only addition, not implemented in the first pass. A dedicated Inference
Endpoint is documented (cost, cold-start elimination, guaranteed availability) but not
implemented — no candidate model here has a demonstrated need for one yet.

**Rationale**: FR-056 requires at least two modes to be supported and the choice
justified. Hosted API avoids committing this machine's 24GB to model weights before any
listening test has justified the choice; local execution is kept for the genuinely small
models so the feature still works without network access to the Hugging Face API.

**Alternatives considered**: local-only for everything — rejected, because `lahgtna-
omnivoice-v2`'s exact per-dialect training status is unverified and a 0.6B TTS model is
a meaningfully larger local commitment than the linguistic-processing models, better
trialled remotely first. A dedicated Endpoint first — rejected as premature spend before
any comparison has shown a model is worth paying to keep warm.

---

## R13. Where dialect detection actually runs in this pipeline

**Decision**: Dialect detection operates on **user-typed Arabic text**, not audio — this
feature has no microphone input (Assumptions: avatar pipeline is documented, not built).
`IbrahimAmin/marbertv2-arabic-written-dialect-classifier` (R11) is therefore the only
detection candidate actually usable by FR-048 today; the audio-based classifiers found in
R11 are recorded for the future avatar pipeline (FR-046), where the input genuinely is a
speech signal, and are explicitly not claimed as usable here.

**Rationale**: An audio dialect classifier cannot be applied to a text request; recording
this explicitly prevents a design that would have picked a well-benchmarked but wrong-
modality model for FR-048's actual acceptance scenarios (Story 6, Scenario 3-4).

**Alternatives considered**: none genuinely competing — this is a modality constraint, not
a quality tradeoff.

---

## R14. What "did Hugging Face help" will actually mean here (methodology)

**Decision**: FR-054's four architectures are compared per dialect using the manual
listening rubric FR-061 requires (naturalness, pronunciation, dialect accuracy, prosody,
English-mixing, voice quality — each out of 5) plus the same TTFA/total-latency/RTF
measurement already built for Edge/Groq/ElevenLabs (R6), so a Hugging Face path is held to
the identical measurement bar as an existing provider rather than a separate, softer one.
A "did it help" answer (FR-062) requires the HF-involving architecture to outscore the
existing-TTS-alone baseline on dialect accuracy specifically, not merely tie or win on an
unrelated axis like voice quality.

**Rationale**: Constitution V forbids a claim without a measurement; defining the pass bar
before generating any audio (rather than after, when a favorable framing becomes tempting)
is what keeps FR-062's eventual answers falsifiable.

**Alternatives considered**: a single blended score — rejected, because a high blended
score could hide a dialect-accuracy loss offset by a voice-quality gain, which would
directly contradict the spec's stated priority that dialect authenticity outweighs voice
cloning/polish (Assumptions).

---

## Resolved Technical Context

| Unknown | Resolution |
|---------|-----------|
| Language/Version | Python 3.12 |
| Primary dependencies | FastAPI, Uvicorn, Pydantic v2, httpx, edge-tts, pytest, pytest-asyncio |
| Storage | None. Benchmark and demo artifacts are files; no database (Principle VIII) |
| Testing | pytest + pytest-asyncio; offline by default, integration tests credential-gated |
| Target platform | Local machine, Linux/macOS, Python 3.12+ |
| Project type | Web service (Python backend) + static demonstration page |
| Performance goals | Preprocessing P95 < 50 ms @ 500 chars (SC-004); audible before synthesis completes (SC-002) |
| Constraints | No credentials required for the default path; no user text or audio logged or persisted |
| Scale/scope | Single concurrent user; prototype, not a hosted service |
| Local HF hardware ceiling | Apple M5, arm64, 24 GB unified memory, MPS/CPU only — measured (R10), not assumed |
| HF execution mode | Hosted Inference API first (credential-gated, optional, like Groq/ElevenLabs); local MPS/CPU for models R11 confirms are small; dedicated Endpoint documented, not implemented (R12) |
| HF dependencies | `huggingface_hub` always; `torch`+`transformers` only behind an optional extra, added when a specific local model from R11 is actually wired up |
