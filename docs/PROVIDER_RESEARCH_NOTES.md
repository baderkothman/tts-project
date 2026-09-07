# Provider Research Notes (evidence gathered 2026-09-07)

Raw evidence captured before specification. Full evaluation lives in `TTS_EVALUATION.md`.

## Excluded by mandate: Azure AI Speech

**Not evaluated as a candidate.** The project brief excludes Azure explicitly (individual
developer, no Azure company/tenant setup) — a policy constraint, not a quality judgment. For
completeness, and because the brief permits a brief mention here: Azure documents 16 Arabic
locales, 40 Arabic voices (Standard Neural), full SSML with `<phoneme>` overrides and custom
lexicon, and $16/1M chars pricing with a 500K-chars/month free tier — it would likely have
scored well on locale/dialect breadth and phoneme control. It is not used anywhere in this
project regardless. Microsoft Edge Neural TTS (below) serves the *same* underlying neural
voice family through a separate, credential-free, non-Azure endpoint — it needs no Azure
account, tenant, key, or region and is not the Azure Speech product.

## Verified locally (executed, not claimed)

- `edge-tts` reachable with **no credentials**: 32 Arabic voices across **16 Arabic locales**
  (ar-AE, ar-BH, ar-DZ, ar-EG, ar-IQ, ar-JO, ar-KW, ar-LB, ar-LY, ar-MA, ar-OM, ar-QA,
  ar-SA, ar-SY, ar-TN, ar-YE) — 2 voices (1F/1M) per locale.
- Real chunked streaming confirmed: 41 audio chunks, 29,376 bytes, cold TTFA 2485 ms,
  total 3011 ms for a 47-char MSA sentence on `ar-SA-HamedNeural`.

## OpenAI TTS (docs, fetched 2026-09-07)

- Six stock voices (alloy, echo, fable, onyx, nova, shimmer), all English-optimized.
  **No Arabic-specific voice.** Arabic input is accepted and produces audio because the TTS
  model generally follows Whisper-family multilingual training, but this is not a documented
  Arabic *capability* — quality and dialect behavior are unverified, not merely unmeasured.
- No Arabic dialect distinction of any kind is published.
- Source: <https://developers.openai.com/api/docs/guides/text-to-speech>

## Gemini API TTS (docs, fetched 2026-09-07)

- Arabic (`ar`) is explicitly listed in Gemini's supported-language table — genuinely
  confirmed, not assumed. 30 generic voice names (Zephyr, Puck, Charon, Kore, Fenrir, Leda,
  …), none Arabic-specific. "TTS models detect the input language automatically" with no
  documented dialect distinction.
- Individually accessible via a Google AI Studio API key — no enterprise/tenant setup,
  unlike Google Cloud TTS (a separate product, see below).
- Source: <https://ai.google.dev/gemini-api/docs/speech-generation>

## Groq — Orpheus Arabic (docs, fetched 2026-09-07)

- **The only preferred-list provider with a genuinely dialect-trained Arabic voice.**
  `canopylabs/orpheus-arabic-saudi`: "Authentic Saudi dialect synthesis" — colloquial
  Saudi/Gulf speech, explicitly distinct from MSA, not a multilingual model with Arabic as
  one of many inputs.
- 6 voices: male — Abdullah, Fahad, Sultan; female — Lulwa, Noura, Aisha.
- Endpoint: `https://api.groq.com/openai/v1/audio/speech` (OpenAI-compatible REST), auth via
  `GROQ_API_KEY` — individual-developer-simple, no enterprise setup.
- **Hard constraint**: 200-character limit on `input` per call. Output is WAV only; no
  streaming or vocal-direction/style-tag support is documented for the Arabic model
  (unlike Groq's separate English Orpheus model, which does support `[cheerful]`-style tags).
- Pricing: $40 / 1M characters. No batch processing for Orpheus models currently.
- Source: <https://console.groq.com/docs/text-to-speech>,
  <https://console.groq.com/docs/text-to-speech/orpheus>

## Hugging Face Arabic models (docs/model cards, fetched 2026-09-07)

Evaluated as models, not as one monolithic "provider" (per the brief's explicit
instruction). Representative dialect-aware options found: `Moeeldouma/arabic-tts-xtts-v2`
(XTTS-v2 fine-tuned across Sudanese/Egyptian/Gulf/Levantine/MSA), `NAMAA-Space/NAMAA-Saudi-TTS`
(Chatterbox-based, colloquial Saudi), `facebook/mms-tts-ara` (Meta's Massively Multilingual
Speech Arabic checkpoint), `IbrahimSalah/F5-TTS-Arabic`. All are **self-hosted only** — none
offers a simple hosted-inference API callable with just an API key the way Groq/ElevenLabs
do; running any of them requires a GPU, which this implementation environment does not have.
**Conclusion**: real and improving Arabic dialect coverage exists on Hugging Face, but as a
**self-hosted Python model**, not a hosted API — not integrated in this prototype's scope,
recorded here as a genuine future option rather than dismissed.

## ElevenLabs (docs)

- Arabic supported across eleven_v3 (70+ langs), multilingual_v2 (29), flash_v2_5 (32),
  turbo_v2_5 (32). No official Arabic *dialect locales* — regional accent varies by voice.
- `flash_v2_5`: ~75 ms model inference latency; streaming via SSE + WebSocket.
- **`<phoneme>` SSML tags are English-only.** For Arabic, pronunciation control is limited to
  **alias substitution** in pronunciation dictionaries; IPA/CMU in non-English requires eleven_v3.
- Pricing: ~$0.10 / 1K chars (v2/v3), ~$0.05 / 1K chars (Flash/Turbo). Free tier 10K chars/mo.

## Google Cloud TTS (docs)

- Arabic exposed as **`ar-XA` = Modern Standard Arabic only**. No dialect locales.
- Chirp 3: HD does **not** support SSML, speaking rate, or pitch.
- Pricing: $4/1M (Standard/WaveNet), $16/1M (Neural2), $30/1M (Chirp 3: HD), $160/1M (Studio).

## Architectural consequence

No integrated provider offers portable Arabic phoneme control: Groq's Orpheus Arabic
accepts no markup at all, ElevenLabs is alias-only for Arabic, and Edge's client escapes
its own input. (Azure has `<phoneme>` and Google Chirp3 has no SSML at all, for context —
neither is integrated, so neither changes this conclusion.) Therefore pronunciation
correction MUST be implemented as **provider-independent orthographic rewriting in Python**
(tashkeel, phonetic respelling, alias substitution); SSML `<phoneme>` remains a
capability-gated hook for a future adapter that declares `phoneme=True`, but nothing in the
current catalogue does.

## Sources

- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- https://azure.microsoft.com/en-us/pricing/details/speech/
- https://developers.openai.com/api/docs/guides/text-to-speech
- https://ai.google.dev/gemini-api/docs/speech-generation
- https://console.groq.com/docs/text-to-speech
- https://console.groq.com/docs/text-to-speech/orpheus
- https://huggingface.co/Moeeldouma/arabic-tts-xtts-v2
- https://huggingface.co/NAMAA-Space/NAMAA-Saudi-TTS
- https://huggingface.co/facebook/mms-tts-ara
- https://elevenlabs.io/docs/models
- https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries
- https://elevenlabs.io/docs/eleven-api/concepts/latency
- https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types
- https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd
