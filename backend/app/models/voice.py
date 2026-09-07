"""Voice metadata (FR-002, FR-003, FR-009, data-model.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Gender = Literal["male", "female", "unknown"]


class Voice(BaseModel):
    """A specific Saudi Arabic speaking identity.

    ``gender`` is a closed three-value set, not a free string, so
    ``"unknown"`` is a real, representable value rather than something a
    caller could mistake for missing data (FR-009: never invent a gender the
    provider does not reliably document).
    """

    id: str
    name: str
    provider: str
    gender: Gender
    dialect: str = "saudi"
    model: str
