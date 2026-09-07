"""Request/response/config dataclasses for the Hugging Face provider package."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.dialect import HFModelConfig


@dataclass
class HFSynthesisRequest:
    """What an execution-mode backend needs to run one synthesis call."""

    text: str
    model: HFModelConfig
    timeout_s: float
    hf_token: str | None


@dataclass
class HFSynthesisResult:
    audio_bytes: bytes
    content_type: str = "audio/wave"
