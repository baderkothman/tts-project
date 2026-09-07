# Arabic TTS Provider Evaluation

Evaluated against the criteria in spec.md FR-043. Sources are cited; nothing here is
asserted from memory or marketing copy (Constitution V). Full raw evidence:
[PROVIDER_RESEARCH_NOTES.md](PROVIDER_RESEARCH_NOTES.md).

**Azure AI Speech is excluded from this evaluation by explicit project mandate** — an
individual developer with no Azure company/tenant setup is the target user, and the brief
instructs Azure be excluded from implementation, provider selection, and fallback
regardless of how it would otherwise score. It is mentioned once, briefly, in
`PROVIDER_RESEARCH_NOTES.md` per the brief's own allowance, and nowhere else.

## Providers evaluated

| Provider | Integrated | Credentials required |
|---|---|---|
| Microsoft Edge Neural TTS | ✅ Yes — the verified default path | None |
| Groq — Orpheus Arabic (Saudi dialect) | ✅ Yes — adapter implemented, credential-gated | `GROQ_API_KEY` |
| ElevenLabs | ✅ Yes — adapter implemented, credential-gated | `ELEVENLABS_API_KEY` |
| OpenAI TTS | Evaluated only — no Arabic-specific voice (docs) | — |
| Gemini API TTS | Evaluated only — Arabic supported, no dialect distinction (docs) | — |
| Hugging Face (XTTS-v2 AR, NAMAA-Saudi-TTS, MMS-TTS-ara, F5-TTS-AR) | Evaluated only — self-hosted, GPU required | — |
| Google Cloud TTS | Evaluated only (not integrated) | — |

## Provider funnel (brief's own evaluation order)

Following the brief's mandated research order — TTS capability exists? → Arabic? → which
dialects? → how many voices? → male+female? → streaming? → latency? → production-suitable?

| Provider | Has TTS? | Arabic? | Dialect-specific voices? | Voices | M+F? | Streaming | Individual-dev API? |
|---|---|---|---|---|---|---|---|
| OpenAI | Yes | Yes (input only) | **No** — 6 generic multilingual voices | 6 | Mixed-gender-coded, not Arabic-specific | Yes (general) | Yes |
| Gemini | Yes | Yes (`ar`, confirmed) | **No** — 30 generic voices, auto-detected language | 30 | Yes, not Arabic-specific | Not confirmed for Arabic | Yes (AI Studio key) |
| Groq | Yes | Yes | **Yes** — Orpheus Arabic Saudi, dialect-trained | 6 (3M/3F) | Yes | **No** (not documented) | Yes (API key) |
| Hugging Face | Yes (self-hosted) | Yes | Yes (community dialect fine-tunes exist) | Varies by model | Varies | Model-dependent | **No** — needs a GPU, not a hosted API |
| ElevenLabs | Yes | Yes | No documented locale codes | Small curated set | Yes | Yes (SSE/WS) | Yes (API key) |

**Conclusion of the funnel**: Groq is the only preferred-list provider whose Arabic voices
are actually dialect-*trained*, not a generic multilingual model reused for Arabic — which
is the specific product gap ("poor or unclear dialect differentiation... incorrect dialect
pronunciation") this prototype targets. That is why it is the second integrated adapter.

## Comparison

| Criterion | Edge | Groq (Orpheus Arabic) | ElevenLabs | OpenAI | Gemini | Google (Chirp 3: HD) |
|---|---|---|---|---|---|---|
| MSA quality | Neural, native Arabic voices | N/A — trained on colloquial Saudi, not MSA | Multilingual, strong prosody | Unverified (English-optimized voices) | Unverified (generic multilingual voices) | Neural, good quality |
| Dialects | **16 published locales** — verified live, but all MSA-trained | **Genuine Saudi/Gulf dialect training** (docs), 1 dialect | No documented locale codes; accent varies by voice | None published | None published | `ar-XA` only (MSA) — no dialects |
| Naturalness/prosody | Standard neural | Not independently rated (no ASR/human-panel tool available in this environment — see DIALECT_EVALUATION.md); live audio was generated and is intelligible | Not independently rated (same tooling gap); live audio generated via `elevenlabs:sarah` and intelligible | Not measured | Not measured | High-fidelity ("HD") |
| Diacritics (tashkeel) | Read if present, not required | Vendor advises supplying diacritics for accuracy | Read if present | Not documented | Not documented | Read if present |
| SSML / phoneme | **None** — client accepts only rate/volume/pitch (verified) | **None documented** — plain text `input` only | **English-only** `<phoneme>`; Arabic needs alias substitution | Not documented | Not documented | **No SSML at all** |
| Emotion/style | **No Arabic voice exposes native styles** (verified against the published voice table) | **No vocal-direction tags for the Arabic model** (English Orpheus model only) | Voice-settings (stability/style) — closer to native | Not documented for Arabic | Natural-language style prompting (general, not Arabic-verified) | 30 style variants (Arabic coverage not confirmed) |
| Code-switching | Handled reasonably by the shared neural model | Not independently verified | Handled by multilingual model | Not independently verified | Not independently verified | Not independently verified |
| Streaming | **Verified live** (chunked, cold TTFA ~2.5s) | **Confirmed absent live** — this project's adapter synthesizes complete audio (200-char-chunked internally); T4 and T7 land together in every live run | **Verified live** — real SSE streaming confirmed, T4 well before T7 in every sample of a clean 33/33 benchmark run | Yes (general) | Not confirmed for Arabic | Not confirmed as streaming |
| TTFA | Measured locally: 1.3–2.9s TTFA on this network path | Measured live: 780–940ms on the first 2 samples, then 4.8–7.9s once a real, vendor-undocumented **10 requests/minute** limit kicked in — see BENCHMARK_RESULTS.md. Not real streaming (T4=T7): this is round-trip time, not TTFA in the Edge/ElevenLabs sense | **Measured live: 494–697ms mean, 522–864ms P95** across all 11 samples — the lowest TTFA of any integrated provider, and genuinely real streaming (not round-trip time like Groq's) | Not measured | Not measured | Not measured |
| Voice count (Arabic) | 32 (16 locales × 2) | 6 (3 male, 3 female) | Small curated set, no locale grouping | 6 generic (not Arabic-specific) | 30 generic (not Arabic-specific) | Limited, MSA-only |
| Custom/cloned voices | Not supported | Not supported | Yes (professional voice cloning) | Not supported | Not supported | Not for Arabic confirmed |
| API/Python quality | `edge-tts` unofficial but stable | OpenAI-compatible REST, official, simple `httpx` integration | Official REST/WS SDK, well documented | Official SDK | Official SDK (google-genai) | Official SDK |
| Individual-developer access | Yes, no signup | Yes, API key only | Yes, API key only | Yes, API key only | Yes, AI Studio key | No — Google Cloud project/billing setup |
| Max input per call | 5000 chars (this pipeline's cap) | **200 chars** (hard vendor limit; adapter chunks transparently) | 5000 chars (this pipeline's cap) | Not documented as a hard limit | Not documented as a hard limit | Not evaluated |
| Cost | Free (unofficial) | $40 / 1M chars, **but see rate limit below — this account's on-demand tier is 10 req/min and 100 req/day, confirmed via live response headers** | $0.05–0.10/1K chars (~$50–100/1M); free tier **can only call voices already in the account's own library, not the public Voice Library** — confirmed live (402 on a library voice, 200 on an account voice) | Not evaluated in depth (out of scope: no Arabic voice) | Not evaluated in depth (out of scope: no dialect) | $4–30/1M depending on tier |
| Production readiness | **No SLA — prototyping only** | Documented API, no SLA published; **10 req/min hard limit confirmed live** makes the on-demand tier unsuitable for a busy conversational avatar without a higher tier | Production-grade, published rate limits — free tier's library-voice restriction (above) is a real gotcha but not a blocker once understood: the ~20 premade voices every account gets by default work immediately | Production-grade (general) | Production-grade (general) | Production-grade |

## Findings only visible with live credentials configured

None of these were visible from documentation alone — exactly the gap live testing exists to
close (Constitution V, "measured, not claimed"):

1. **Groq's Orpheus Arabic model enforces 10 requests/minute** on the on-demand tier (and a
   100 requests/day cap, read from live `x-ratelimit-*` response headers) — not stated on the
   model's docs page fetched during research. A single benchmark run at 3 repetitions/sample
   across 11 samples (44 potential calls) reliably exceeds it; the adapter now retries once,
   honoring the vendor's `Retry-After` header, which recovers most but not all of a burst
   (see `docs/BENCHMARK_RESULTS.md` for the exact run where 8/11 samples succeeded, the last
   3 did not, and the climbing TTFA in between is the backoff wait itself, shown not hidden).
2. **ElevenLabs' free tier rejects API calls to public "Voice Library" voices**
   (`402 payment_required`, `"Free users cannot use library voices via the API"`) — but only
   for voices *not already in the account's own library*. This distinction was not obvious
   from the error message alone: "Rachel" (ElevenLabs' own commonly-documented example
   voice) is a library voice and hit the 402; "Adam" happened to already be in this
   account's default set and worked immediately. The real fix required two steps, both
   live-verified before adopting: (a) the configured API key was initially scoped without
   `voices_read`, so the account's own voice library couldn't even be queried (401) until
   that permission was granted; (b) once queryable, the account's ~20 default premade
   voices were listed and one — "Sarah" — was confirmed live to synthesize real Arabic audio
   before replacing Rachel with it in the catalogue. A clean 33/33-call benchmark followed
   (`docs/BENCHMARK_RESULTS.md`) — this is now a fully working, live-verified provider, not
   a documented limitation.

## Recommendations

1. **Best MSA quality**: Edge (Microsoft neural voices) — the only evaluated provider with
   verified, live-tested native Arabic MSA neural synthesis in this project's scope.
2. **Best dialect authenticity**: Groq's Orpheus Arabic (Saudi) — the only preferred-list
   provider whose Arabic model is dialect-*trained* rather than a generic multilingual voice
   pressed into Arabic service; see [DIALECT_EVALUATION.md](DIALECT_EVALUATION.md).
3. **Best real-time/avatar option**: **ElevenLabs, live-confirmed** — 494–864ms TTFA (mean
   to P95) across all 11 samples, genuine SSE streaming (T4 well before T7), zero failures
   over 33 live calls (`docs/BENCHMARK_RESULTS.md`). This is the lowest TTFA and the only
   confirmed-genuine streaming behavior of the three integrated providers, once its
   account-configuration gotcha (below) is handled correctly. **Groq's Arabic model remains
   unsuitable for this use case** by contrast — no streaming at all, and a 10 req/min ceiling
   a single conversational session could exhaust in well under a minute.
4. **Best pronunciation control**: None of the three integrated providers offers portable
   phoneme control for Arabic — see research.md R4. This project's answer is
   provider-independent orthographic rewriting (`docs/PRONUNCIATION.md`), which works
   regardless of which provider is behind it.
5. **Best individual-developer accessibility**: Edge (no signup, no limits encountered) is
   the clear winner once live-tested. ElevenLabs' signup is simple and, once a voice already
   in the account's own library is used (not one of the public "Voice Library" voices most
   documentation examples reference), it is fully usable on the free tier — a real gotcha,
   now resolved and documented, not a hard blocker. Groq is a single API key away but its
   real, live throughput ceiling (10/min, 100/day on this account) is a genuine accessibility
   cost for anything beyond occasional use. Google Cloud TTS remains the least accessible
   integrated-candidate option (enterprise billing/project setup) — the same reasoning that
   excludes Azure, independent of the explicit mandate.

## Why this project's default is Edge, and its second adapter is Groq

Documented in [research.md](../specs/001-arabic-tts-prototype/research.md) R1: no paid
credentials were available in the implementation/target environment, so Edge is the only
path that let every acceptance criterion — including the pronunciation demo, which per
Constitution V must be built from something actually observed — be verified against real
audio rather than assumed. Groq was chosen as the second, credential-gated adapter over
OpenAI and Gemini specifically because it is the only one of the four preferred providers
(OpenAI, Gemini, Groq, Hugging Face) with a genuinely dialect-trained Arabic voice, which is
this project's stated core problem to solve — not because it scored best on every criterion
(it does not stream, and its 200-character request cap is a real integration cost this
project's adapter has to work around).
