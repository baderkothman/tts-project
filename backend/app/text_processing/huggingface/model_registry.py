"""Thin accessor over `data/hf_model_registry.py` (FR-055).

The only module the other Hugging Face linguistic-processing services import
from for model lookup — keeps `data/hf_model_registry.py` the single place a
`repo_id` is named, per research.md R11/FR-058.
"""

from __future__ import annotations

from backend.app.data.hf_model_registry import enabled_for_task, get
from backend.app.models.dialect import HFModelConfig

__all__ = ["get", "enabled_for_task", "first_enabled"]


def first_enabled(task: str) -> HFModelConfig | None:
    """The first enabled registry entry for a task, or None (FR-057: a
    caller must treat "no enabled model" as a normal, handled state)."""
    candidates = enabled_for_task(task)
    return candidates[0] if candidates else None
