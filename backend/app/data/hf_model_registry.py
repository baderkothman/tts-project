"""The Hugging Face Model Evaluation Matrix, as loadable data (FR-055, FR-058).

Mirrors `specs/001-arabic-tts-prototype/research.md` R11 exactly — every
`HFModelConfig` here traces to a model card or paper actually fetched and
read before this file was written (Constitution V). Nothing is downloaded by
importing this module; `enabled=True` only marks a model as *eligible* for a
live call, gated separately by `Settings.has_huggingface()` at the point of
use (providers/huggingface/, text_processing/huggingface/).

Routing code MUST read from this registry rather than hardcode a `repo_id`
(FR-055) — this is the only place a specific repo_id may be named outside
this file and research.md itself.
"""

from __future__ import annotations

from backend.app.models.dialect import HFModelConfig

# --- Enabled: cleared research.md R11 on relevance, license, and size/hardware ---

HF_MODEL_REGISTRY: list[HFModelConfig] = [
    HFModelConfig(
        id="dialect-classifier-marbertv2",
        repo_id="IbrahimAmin/marbertv2-arabic-written-dialect-classifier",
        task="dialect_classification",
        dialects=["msa", "gulf", "egyptian", "levantine", "maghrebi"],
        local_supported=True,  # 200M params, CPU-viable per card (R10 ceiling)
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=None,
        license="Apache-2.0",
        enabled=True,
        source_url="https://huggingface.co/IbrahimAmin/marbertv2-arabic-written-dialect-classifier",
        notes=(
            "Text-in classifier (research.md R13) — the only detection candidate "
            "usable for FR-048's actual input (typed text, not audio). Does not "
            "distinguish Lebanese from Levantine (FR-051 applies). Live-confirmed "
            "2026-09-07 with a real HF_TOKEN (permission inference.serverless.write "
            "granted): Hugging Face returns 410 Gone via hf-inference — 'the "
            "requested model is deprecated and no longer supported by provider "
            "hf-inference'. A genuine, confirmed platform constraint, not a "
            "token or code defect (docs/DIALECT_EVALUATION.md)."
        ),
    ),
    HFModelConfig(
        id="diacritizer-flan-t5-small",
        repo_id="Abdou/arabic-tashkeel-flan-t5-small",
        task="diacritization",
        dialects=["msa"],  # no dialect-specific diacritization claim on the card
        local_supported=True,
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=None,
        license=None,  # not confirmed in research.md R11 — see notes
        enabled=False,
        source_url="https://huggingface.co/Abdou/arabic-tashkeel-flan-t5-small",
        notes=(
            "License was not confirmed on the model card during R11 research — "
            "left disabled until confirmed, per FR-058 (an unverified license "
            "blocks use, it is not treated as implicitly permissive)."
        ),
    ),
    HFModelConfig(
        id="g2p-charsiu-byt5-tiny",
        repo_id="charsiu/g2p_multilingual_byT5_tiny_16_layers_100",
        task="g2p",
        dialects=["msa"],  # no dialect-aware phoneme mapping documented
        local_supported=True,  # smallest ByT5 variant in the family
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=None,
        license=None,  # not confirmed in research.md R11 — see notes
        enabled=False,
        source_url="https://huggingface.co/charsiu/g2p_multilingual_byT5_tiny_16_layers_100",
        notes=(
            "License was not confirmed on the model card during R11 research — "
            "left disabled until confirmed, per FR-058."
        ),
    ),
    HFModelConfig(
        id="egyptian-tts-chatterbox",
        repo_id="oddadmix/chatterbox-egyptian-v0",
        task="dialect_tts",
        dialects=["egyptian"],
        local_supported=True,  # 0.5B params, CPU/CUDA flexible per card
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=None,
        license="MIT",
        enabled=True,
        source_url="https://huggingface.co/oddadmix/chatterbox-egyptian-v0",
        notes=(
            "Cleanest license of the dialect-specific TTS candidates found in "
            "R11. Live-confirmed 2026-09-07 with a real HF_TOKEN (permission "
            "inference.serverless.write granted): Hugging Face's Inference "
            "Providers system returns 400 'Model not supported by provider "
            "hf-inference' for this repo_id — its own model metadata shows "
            "inference:null, meaning no provider has deployed it. This is a "
            "genuine, confirmed platform constraint, not a token or code "
            "defect (docs/DIALECT_EVALUATION.md). Left enabled=True because "
            "the license/relevance case still holds — a future Dedicated "
            "Inference Endpoint or local execution could still serve it."
        ),
    ),
    # --- Disabled: recorded per FR-058 so the exclusion reason stays legible ---
    HFModelConfig(
        id="lahgtna-omnivoice-v2",
        repo_id="oddadmix/lahgtna-omnivoice-v2",
        task="dialect_tts",
        dialects=[],  # per-dialect training status not verifiable from the card
        local_supported=True,
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=2.4,  # 0.6B params, fp16 estimate
        license=None,
        enabled=False,
        source_url="https://huggingface.co/oddadmix/lahgtna-omnivoice-v2",
        notes=(
            "Broad dialect roadmap (Lebanon, Gulf states, etc.) but the card "
            "does not state which are actually trained vs. planned, and no "
            "license is stated. Both must be confirmed before this is "
            "scored, not merely fetched (research.md R11)."
        ),
    ),
    HFModelConfig(
        id="mms-tts-ara-msa",
        repo_id="facebook/mms-tts-ara",
        task="dialect_tts",
        dialects=["msa"],
        local_supported=True,  # 36.3M params, trivially small
        remote_supported=True,
        streaming=False,
        requires_gpu=False,
        approximate_vram_gb=0.2,
        license="CC-BY-NC-4.0",
        enabled=False,
        source_url="https://huggingface.co/facebook/mms-tts-ara",
        notes="Non-commercial license — usable only as an MSA comparison point in FR-054's architecture matrix, never as a production candidate.",
    ),
    HFModelConfig(
        id="voxlect-dialect-id-mms-lid-256",
        repo_id="tiantiaf/voxlect-arabic-dialect-mms-lid-256",
        task="dialect_classification",
        dialects=["msa", "gulf", "egyptian", "levantine", "maghrebi"],
        local_supported=False,  # 1B params, GPU expected per card
        remote_supported=True,
        streaming=False,
        requires_gpu=True,
        approximate_vram_gb=4.0,
        license="CC-BY-NC-4.0",
        enabled=False,
        source_url="https://huggingface.co/tiantiaf/voxlect-arabic-dialect-mms-lid-256",
        notes="Audio-in (wrong modality for FR-048's typed-text input) and non-commercial licensed — rejected twice over. Recorded for the documented, not-built, future avatar pipeline (FR-046).",
    ),
]


def get(model_id: str) -> HFModelConfig | None:
    """Look up a registry entry by id. Never raises (mirrors provider.available())."""
    for entry in HF_MODEL_REGISTRY:
        if entry.id == model_id:
            return entry
    return None


def enabled_for_task(task: str) -> list[HFModelConfig]:
    return [e for e in HF_MODEL_REGISTRY if e.task == task and e.enabled]
