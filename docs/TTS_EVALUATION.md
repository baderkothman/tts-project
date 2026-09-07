# Arabic TTS Provider Evaluation

Evaluated against the criteria in spec.md FR-043. Sources are cited; nothing
here is asserted from memory or marketing copy (Constitution V). Full raw
evidence: [PROVIDER_RESEARCH_NOTES.md](PROVIDER_RESEARCH_NOTES.md).

## Providers evaluated

| Provider | Integrated | Credentials required |
|---|---|---|
| Microsoft Edge Neural TTS | ✅ Yes — the verified default path | None |
| Azure AI Speech | ✅ Yes — adapter implemented, credential-gated | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |
| ElevenLabs | ✅ Yes — adapter implemented, credential-gated | `ELEVENLABS_API_KEY` |
| Google Cloud TTS | Evaluated only (not integrated) | — |

## Comparison

| Criterion | Edge / Azure (same voice family) | ElevenLabs | Google (Chirp 3: HD) |
|---|---|---|---|
| MSA quality | Neural, native Arabic voices | Multilingual, strong prosody | Neural, good quality |
| Dialects | **16 published locales** — verified live | No documented locale codes; accent varies by voice | `ar-XA` only (MSA) — no dialects |
| Naturalness/prosody | Standard neural | Generally rated more expressive | High-fidelity ("HD") |
| Diacritics (tashkeel) | Read if present, not required | Read if present | Read if present |
| SSML / phoneme | **Azure: full SSML + Arabic `<phoneme>`.** Edge: none (verified — client accepts only rate/volume/pitch) | **English-only** `<phoneme>`; Arabic needs alias substitution | **No SSML at all** |
| Emotion/style | **No Arabic voice exposes native styles** (verified against the published voice table) | Voice-settings (stability/style) — closer to native | 30 style variants (language coverage for Arabic not confirmed) |
| Code-switching | Handled reasonably by the shared neural model | Handled by multilingual model | Not independently verified |
| Streaming | **Edge: verified live** (chunked, cold TTFA ~2.5s). Azure: chunked REST, same voices | SSE + WebSocket; Flash ~75ms model latency | Not confirmed as streaming |
| TTFA | Edge measured locally: 1.3–2.9s TTFA on this network path | ~75ms model inference (excludes network) | Not measured |
| Voice count (Arabic) | 32 (16 locales × 2) | Small curated set, no locale grouping | Limited, MSA-only |
| Custom/cloned voices | Not supported | Yes (professional voice cloning) | Not for Arabic confirmed |
| API/Python quality | `edge-tts` unofficial but stable; Azure REST is official and documented | Official REST/WS SDK, well documented | Official SDK |
| Cost | Edge: free (unofficial). Azure: $16/1M chars (500K free/mo) | $0.05–0.10/1K chars (~$50–100/1M) | $4–30/1M depending on tier |
| Production readiness | **Edge has no SLA — prototyping only.** Azure is production-grade | Production-grade, published rate limits | Production-grade |

## Recommendations

1. **Best Arabic quality**: Azure AI Speech — same neural voices as Edge, but with an SLA, documented rate limits, and full SSML control.
2. **Best real-time/avatar option**: ElevenLabs Flash — sub-100ms model latency and WebSocket bidirectional streaming purpose-built for conversational use.
3. **Best pronunciation control**: Azure — the only evaluated provider with Arabic `<phoneme>` SSML support; ElevenLabs and Google offer no comparable Arabic-specific control.
4. **Best dialect support**: Azure/Edge — 16 published Arabic locales vs. Google's single MSA locale and ElevenLabs' undocumented accent variation.
5. **Best cost/quality balance**: Edge for prototyping (free, same voice quality as Azure) → Azure for production at the same voice quality with an SLA.

## Why this project defaults to Edge

Documented in [research.md](../specs/001-arabic-tts-prototype/research.md) R1:
no credentials were available in the implementation/target environment. Edge
is the only path that let every acceptance criterion — including the
pronunciation demo, which per Constitution V must be built from something
actually observed — be verified against real audio rather than assumed.
