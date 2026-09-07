# Voice Catalog

Every voice this prototype can actually route to, grouped as the brief's own
`Dialect → Gender → Voice` structure requires. Generated from
`backend/app/data/voices.py`, the single source of truth also read by the running app's
`GET /api/voices` endpoint — this table cannot drift from what the app serves because it
lists the same catalogue, not a separately maintained description of it.

## Microsoft Edge Neural TTS (`edge`) — 32 voices, 16 locales, MSA-trained

No credentials required. All 16 published Arabic locales, one female and one male voice
each. See [DIALECT_EVALUATION.md](DIALECT_EVALUATION.md) for what "MSA-trained" means here
versus Groq's genuine dialect training below — locale breadth, not dialect authenticity.

| Dialect family | Locale | Country | Female | Male |
|---|---|---|---|---|
| MSA | ar-SA | Saudi Arabia | Zariyah | Hamed |
| Gulf | ar-AE | UAE | Fatima | Hamdan |
| Gulf | ar-KW | Kuwait | Noura | Fahed |
| Gulf | ar-QA | Qatar | Amal | Moaz |
| Gulf | ar-BH | Bahrain | Laila | Ali |
| Gulf | ar-OM | Oman | Aysha | Abdullah |
| Gulf | ar-IQ | Iraq | Rana | Bassel |
| Egyptian | ar-EG | Egypt | Salma | Shakir |
| Levantine | ar-LB | Lebanon | Layla | Rami |
| Levantine | ar-SY | Syria | Amany | Laith |
| Levantine | ar-JO | Jordan | Sana | Taim |
| Maghrebi | ar-MA | Morocco | Mouna | Jamal |
| Maghrebi | ar-DZ | Algeria | Amina | Ismael |
| Maghrebi | ar-TN | Tunisia | Reem | Hedi |
| — (no defensible family claim, FR-027) | ar-LY | Libya | Iman | Omar |
| — (no defensible family claim, FR-027) | ar-YE | Yemen | Maryam | Saleh |

## Groq — Orpheus Arabic (`groq`) — 6 voices, 1 locale, Saudi/Gulf-dialect-trained

Requires `GROQ_API_KEY`. All six voices share the `ar-SA` locale string but carry
`dialect=gulf` (not `msa`) — a genuinely dialect-trained model, per research R1. No
streaming; the adapter transparently chunks input over the vendor's 200-char-per-call limit.

| Gender | Voice |
|---|---|
| Male | Abdullah |
| Male | Fahad |
| Male | Sultan |
| Female | Lulwa |
| Female | Noura |
| Female | Aisha |

## ElevenLabs (`elevenlabs`) — 2 voices, no documented Arabic locale

Requires `ELEVENLABS_API_KEY`. No Arabic dialect locale is published by the vendor, so per
FR-027 these carry `dialect=None` rather than an inferred family — Arabic text is accepted
through general multilingual capability, not a dialect-specific model.

**Live-verified voice-selection constraint** (`docs/TTS_EVALUATION.md`): the free tier's API
only accepts voices already present in the account's own library, not the public Voice
Library — "Rachel", ElevenLabs' commonly-documented example voice, is a library voice and is
rejected (402) on a fresh account. Both voices below are confirmed live, working members of
this account's own library (`GET /v1/voices`), not assumed from vendor documentation.

| Gender | Voice | Notes |
|---|---|---|
| Female | Sarah | Multilingual, Arabic-capable (no dialect claim); confirmed live |
| Male | Adam | Multilingual, Arabic-capable (no dialect claim); confirmed live |

## Hugging Face (`huggingface`) — 1 voice, experimental, credential-gated

Requires `HF_TOKEN`. Unlike Edge/Groq/ElevenLabs, this catalogue is generated from
`data/hf_model_registry.py`'s `enabled=True`, `task="dialect_tts"` entries only (FR-058) —
nothing here was added without clearing the Model Evaluation Matrix's license/relevance
check first (`docs/HF_MODEL_RESEARCH.md`).

| Gender | Model | Dialect | Live-verified? |
|---|---|---|---|
| Unknown/unspecified | `oddadmix/chatterbox-egyptian-v0` | Egyptian | **No** — no `HF_TOKEN` was configured in this session; `scripts/observe_dialect_tts.py` is ready to confirm it the moment one is |

**Gender is "Unknown/unspecified" by design (FR-059)**, not a placeholder: no speaker or
gender metadata is documented on this model's card, and inventing one would be exactly the
kind of unverified claim Constitution V forbids.

## Dialect Profiles (US6-7, FR-049)

Six `DialectProfile` records (`data/dialect_profiles.py`) route a resolved dialect to its
processing and synthesis path — narrower than the `Dialect` locale-routing family above
where no provider backs the extra granularity (e.g. `lebanese`/`saudi` share their broader
family's provider voices, honestly, rather than inventing a locale no vendor publishes).

| Dialect Profile | Family (routing) | HF-native TTS? | Existing-provider fallback |
|---|---|---|---|
| `msa` | msa | No | Edge `ar-SA` |
| `levantine` | levantine | No candidate cleared R11 | Edge `ar-LB`/`ar-SY`/`ar-JO` |
| `lebanese` | levantine | No candidate cleared R11 | Edge `ar-LB` |
| `gulf` | gulf | No candidate cleared R11 | Edge `ar-AE`, Groq (dialect-trained) |
| `saudi` | gulf | No candidate cleared R11 | **Groq Orpheus Arabic** (dialect-trained, not just locale-routed) |
| `egyptian` | egyptian | Eligible, **not yet listening-confirmed** (`oddadmix/chatterbox-egyptian-v0`) | Edge `ar-EG` |

## Totals

| Provider | Voices | Locales | Dialect families claimed | Credentials |
|---|---|---|---|---|
| Edge | 32 | 16 | MSA, Gulf, Egyptian, Levantine, Maghrebi | None |
| Groq | 6 | 1 (ar-SA) | Gulf (dialect-trained) | `GROQ_API_KEY` |
| ElevenLabs | 2 | 0 published | None (FR-027) | `ELEVENLABS_API_KEY` |
| Hugging Face | 1 (experimental, unverified) | 1 (ar-EG, unconfirmed) | Egyptian (candidate, not listening-confirmed) | `HF_TOKEN` |
| **Total** | **41** | — | 5 families across ≥1 provider each, +1 candidate pending verification | — |

## Voice browser behavior

Selecting a dialect filters to only the voices that family maps to, per provider (never a
generic "Arabic" option — the brief's explicit requirement). Selecting a provider first
further narrows the list to that provider's own catalogue; `GET /api/voices` accepts both
`provider` and `locale` query filters, and the frontend's dialect/gender selectors compose
on top of whichever provider is active, never showing a voice the selected provider does not
actually serve (`test_api_voices.py`, `test_voice_router.py`).
