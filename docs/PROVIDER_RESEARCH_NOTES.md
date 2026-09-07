# Provider Research Notes (evidence gathered 2026-09-07)

Raw evidence captured before specification. Full evaluation lives in `TTS_EVALUATION.md`.

## Verified locally (executed, not claimed)

- `edge-tts` reachable with **no credentials**: 32 Arabic voices across **16 Arabic locales**
  (ar-AE, ar-BH, ar-DZ, ar-EG, ar-IQ, ar-JO, ar-KW, ar-LB, ar-LY, ar-MA, ar-OM, ar-QA,
  ar-SA, ar-SY, ar-TN, ar-YE) — 2 voices (1F/1M) per locale.
- Real chunked streaming confirmed: 41 audio chunks, 29,376 bytes, cold TTFA 2485 ms,
  total 3011 ms for a 47-char MSA sentence on `ar-SA-HamedNeural`.
- The Edge voice list is **identical** to the documented Azure Arabic neural voice list,
  confirming the same underlying Microsoft neural voice family.

## Azure AI Speech (docs)

- 16 Arabic locales, 40 Arabic voices total, all **Standard Neural**.
- **No Arabic voice supports speaking styles or roles.** None are Neural HD or multilingual.
  => Emotion for Arabic on Azure/Edge must be synthesised from **prosody** (rate/pitch/volume),
     not from a `style` attribute.
- Full SSML: prosody, emphasis, break, `<phoneme>` overrides, custom lexicon.
- Pricing: $16 / 1M chars standard neural; 500K chars/month free tier.
  Neural HD reduced Mar 2026 from $30 to $22 / 1M chars.

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

No single provider offers portable Arabic phoneme control:
Azure has `<phoneme>`, ElevenLabs is alias-only for Arabic, Google Chirp3 has no SSML at all.
Therefore pronunciation correction MUST be implemented primarily as **provider-independent
orthographic rewriting in Python** (tashkeel, phonetic respelling, alias substitution),
with SSML `<phoneme>` used only as a provider-specific enhancement where supported.

## Sources

- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- https://azure.microsoft.com/en-us/pricing/details/speech/
- https://elevenlabs.io/docs/models
- https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries
- https://elevenlabs.io/docs/eleven-api/concepts/latency
- https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types
- https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd
