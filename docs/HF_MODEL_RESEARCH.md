# Hugging Face Model Research

The full Model Evaluation Matrix (FR-058) behind `backend/app/data/hf_model_registry.py`.
Every row was checked against a real Hugging Face model card (or its linked GitHub
repo/paper) via `WebSearch`/`WebFetch` before being recorded here — nothing below was
downloaded before its relevance, license, and size/hardware fit were confirmed. Full
narrative reasoning and decisions are in
`specs/001-arabic-tts-prototype/research.md` R10-R14; this document is the
practitioner-facing summary FR-058 requires.

## Local hardware ceiling (measured, not assumed)

`sysctl` on the development machine: **Apple M5, arm64, 24 GB unified memory, no discrete
GPU** — so PyTorch execution here is MPS or CPU only, with unified memory (not a separate
VRAM pool) as the real ceiling. A model in the low hundreds of millions of parameters is
comfortable; a documented "GPU recommended"/1B+-parameter model is not treated as locally
viable regardless of its unified-memory theoretical fit.

## Model Evaluation Matrix

| Model | Task | Dialects | Speakers | Male | Female | Voice cloning | Diacritics | Phoneme input | Streaming | Size | CPU viable | Apple Silicon viable | GPU recommended | VRAM | License | Commercial use | Enabled |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [`IbrahimAmin/marbertv2-arabic-written-dialect-classifier`](https://huggingface.co/IbrahimAmin/marbertv2-arabic-written-dialect-classifier) | Dialect classification (text) | MSA/Gulf/Egyptian/Levantine/Maghreb | n/a | n/a | n/a | No | n/a | n/a | No | 200M | Yes | Yes | No | — | Apache-2.0 | Yes | **Yes** |
| [`Abdou/arabic-tashkeel-flan-t5-small`](https://huggingface.co/Abdou/arabic-tashkeel-flan-t5-small) | Diacritization | MSA only | n/a | n/a | n/a | No | Yes (output) | No | No | ~60-80M (T5-small class) | Yes | Yes | No | — | **Unconfirmed** | Unconfirmed | No — license unverified |
| [`charsiu/g2p_multilingual_byT5_tiny_16_layers_100`](https://huggingface.co/charsiu/g2p_multilingual_byT5_tiny_16_layers_100) | G2P | 100 languages incl. Arabic (MSA-oriented, no dialect mapping) | n/a | n/a | n/a | No | No | Yes (output) | No | Tiny ByT5 variant | Yes | Yes | No | — | **Unconfirmed** | Unconfirmed | No — license unverified |
| [`oddadmix/chatterbox-egyptian-v0`](https://huggingface.co/oddadmix/chatterbox-egyptian-v0) | Dialect TTS | Egyptian only | Not documented | Unknown | Unknown | Not evaluated | No | No | No | 0.5B | Yes (CPU/CUDA flexible per card) | Yes | No | — | **MIT** | Yes | **Yes** — pending live listening confirmation (T144) |
| [`oddadmix/lahgtna-omnivoice-v2`](https://huggingface.co/oddadmix/lahgtna-omnivoice-v2) | Dialect TTS | Roadmap claims Egypt/Gulf/Levant/Maghreb/etc.; per-dialect *trained* status unverifiable from the card | Not documented | Unknown | Unknown | Not evaluated | Accepts diacritized input | No | Not documented | 0.6B (Qwen3-0.6B base) | Yes | Yes (also ships `mlx-community/OmniVoice`) | No | ~2.4GB est. | **Unconfirmed** | Unconfirmed | No — license and per-dialect claim both unverified |
| [`ehabnegm/lahgtna-omnivoice-egyptian-v3`](https://huggingface.co/ehabnegm/lahgtna-omnivoice-egyptian-v3) | Dialect TTS | Egyptian only | Not documented | Unknown | Unknown | Not evaluated | Not documented | No | Not documented | ~0.6B | Yes | Yes | No | ~2.4GB est. | **Unconfirmed** | Unconfirmed | No — not yet researched past initial discovery; narrower claim than v2, a candidate for a follow-up pass |
| [`facebook/mms-tts-ara`](https://huggingface.co/facebook/mms-tts-ara) | TTS (baseline) | MSA only | Single speaker | Unknown | Unknown | No | No | No | No | 36.3M / 122MB | Yes, trivially | Yes | No | ~0.2GB | CC-BY-NC-4.0 | **No** | No — non-commercial license; usable only as an FR-054 comparison point |
| [`badrex/mms-300m-arabic-dialect-identifier`](https://huggingface.co/badrex/mms-300m-arabic-dialect-identifier) | Dialect classification (**audio**) | MSA/Egyptian/Gulf/Levantine/Maghrebi | n/a | n/a | n/a | No | n/a | n/a | No | 300M | Yes | Yes | No | — | CC-BY-4.0 | Yes | No — wrong modality for this feature's typed-text input (FR-048); recorded for the documented future avatar pipeline (FR-046) |
| [`tiantiaf/voxlect-arabic-dialect-mms-lid-256`](https://huggingface.co/tiantiaf/voxlect-arabic-dialect-mms-lid-256) | Dialect classification (**audio**) | Egyptian/Levantine/Maghrebi/MSA/Peninsular | n/a | n/a | n/a | No | n/a | n/a | No | 1.0B | Borderline — GPU expected per card | No | Yes | ~4GB | **CC-BY-NC-4.0, explicit "no commercial use"** | **No** | No — rejected twice over (wrong modality + non-commercial license) |
| [CATT (Character-based Arabic Tashkeel Transformer)](https://github.com/abjadai/catt) | Diacritization | MSA | n/a | n/a | n/a | No | Yes (SOTA at publication: 30.83%/35.21% relative DER improvement) | No | No | ~50-100M est. | Yes (size-wise) | Yes (size-wise) | No | — | Not stated in the fetched paper page | Unconfirmed | No — **not distributed as a Hugging Face model repo** (GitHub Release `.pt` checkpoints, loaded via a custom package); would need a local-only backend, not the hosted-API-first default |

## Rejected / not pursued, and exactly why

- **`facebook/mms-tts-ara`** — non-commercial license (CC-BY-NC-4.0). Kept only as a
  documented MSA comparison point in the FR-054 architecture matrix, never as a production
  candidate.
- **`tiantiaf/voxlect-arabic-dialect-mms-lid-256`** — audio-input classifier (wrong modality
  for this feature's typed-text dialect detection) *and* non-commercial licensed. Recorded
  for the documented, not-built, future avatar pipeline instead.
- **`badrex/mms-300m-arabic-dialect-identifier`** — permissively licensed and CPU-viable, but
  still an audio-input classifier; this feature has no microphone input to give it.
- **`oddadmix/lahgtna-omnivoice-v2`** — the broadest-looking dialect-TTS candidate found, but
  its model card does not state which dialects on its roadmap are actually trained versus
  planned, nor a license — both would need direct confirmation (e.g. opening an issue,
  testing generation quality per dialect) before it could be scored, let alone used.
- **`Abdou/arabic-tashkeel-flan-t5-small`**, **`charsiu/g2p_multilingual_byT5_tiny_16_layers_100`**
  — both structurally ready (small, hosted-API-reachable, `text_processing/huggingface/`
  modules already call them) but left `enabled=False` because their license was not
  confirmed during this research pass — an oversight to close in a follow-up, not a rejection
  on merit.
- **CATT** — the strongest diacritization *quality* signal found (beats GPT-4-turbo on its
  own benchmark), excluded from the hosted-API-first default purely because of its
  distribution mechanism (GitHub Release checkpoints, not a Hugging Face Hub repo). Recorded
  as the best candidate for a future local-only backend, not discarded.

## What was actually wired in vs. recorded as a lead

| Registry id | Status | Where |
|---|---|---|
| `dialect-classifier-marbertv2` | Live-integrated code path (`text_processing/huggingface/dialect_classifier.py`, `POST /api/dialect/resolve`) — **live-tested 2026-09-07 with a real, correctly-permissioned `HF_TOKEN`: confirmed `410 Gone`, "deprecated and no longer supported by provider hf-inference."** A genuine platform constraint, not a code or credential defect (`docs/DIALECT_EVALUATION.md`). Degrades gracefully; no dialect resolution is blocked by this, it just never gets a live classifier opinion today. | Enabled |
| `egyptian-tts-chatterbox` | Provider-conformant voice exists (`providers/huggingface/provider.py`) — **live-tested 2026-09-07 with the same real token: confirmed `400 Bad Request`, "Model not supported by provider hf-inference"** (model card shows `inference: null`). Same conclusion as above — a Dedicated Inference Endpoint or local execution would be needed to actually use this model, not just a token. | Enabled |
| `diacritizer-flan-t5-small` | Module ready (`text_processing/huggingface/diacritizer.py`); disabled pending license confirmation — untested by the above, since it was never reached | Disabled |
| `g2p-charsiu-byt5-tiny` | Module ready (`text_processing/huggingface/g2p.py`); disabled pending license confirmation — untested by the above | Disabled |
| `lahgtna-omnivoice-v2`, `mms-tts-ara-msa`, `voxlect-dialect-id-mms-lid-256` | Research leads only — recorded with an explicit rejection/pending reason, no code path calls them | Disabled |

**A separate, real bug found and fixed during the live-testing pass above**: the raw `httpx`
calls in `text_processing/huggingface/{dialect_classifier,diacritizer,g2p}.py` were pointed
at `api-inference.huggingface.co` — Hugging Face's legacy free-tier hostname, which no
longer resolves in DNS at all (confirmed via direct `host`/`nslookup`). Fixed to
`router.huggingface.co/hf-inference/models`, the current Inference Providers gateway. This
fix is what let the two findings above surface as clean, mappable HTTP errors instead of an
opaque connection failure.
