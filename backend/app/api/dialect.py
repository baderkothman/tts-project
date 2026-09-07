"""Dialect resolution and raw-vs-corrected comparison endpoints (US6-7).

Per contracts/http-api.md: a Hugging Face degradation (missing HF_TOKEN,
model unavailable, timeout) is reported as `200` with the reason stated
plainly, never a `5xx` — a known, handled condition, not a service failure
(FR-057, AC-13).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter

from backend.app.models.dialect import DialectComparisonResult, DialectDetectionResult
from backend.app.models.tts import MAX_INPUT_CHARS
from backend.app.providers.registry import get_registry
from backend.app.services import dialect_service

router = APIRouter(prefix="/api/dialect", tags=["dialect"])


class DialectRequest(BaseModel):
    text: str = Field(..., max_length=MAX_INPUT_CHARS)
    dialect: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return v


@router.post("/resolve", response_model=DialectDetectionResult)
async def resolve(request: DialectRequest) -> DialectDetectionResult:
    registry = get_registry()
    return await dialect_service.resolve(
        request.text, dialect=request.dialect, hf_token=registry.settings.hf_token
    )


@router.post("/compare", response_model=DialectComparisonResult)
async def compare(request: DialectRequest) -> DialectComparisonResult:
    registry = get_registry()
    return await dialect_service.compare(
        request.text,
        dialect=request.dialect,
        registry=registry,
        hf_token=registry.settings.hf_token,
        timeout_s=registry.settings.tts_request_timeout_s,
    )
