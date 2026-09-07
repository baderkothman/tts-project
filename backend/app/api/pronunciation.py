"""Pronunciation demo endpoints (FR-019, FR-020)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.models.tts import PronunciationDemo
from backend.app.text_processing.dictionary import PRONUNCIATION_DEMO

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])

_AUDIO_DIR = Path(__file__).resolve().parents[3] / "docs" / "audio"


@router.get("/demo", response_model=PronunciationDemo)
async def get_demo() -> PronunciationDemo:
    return PRONUNCIATION_DEMO


@router.get("/demo/audio")
async def get_demo_audio(corrected: bool = False) -> FileResponse:
    variant = "after" if corrected else "before"
    path = _AUDIO_DIR / f"ilm-ambiguous-{variant}.mp3"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Demo audio not generated yet — run scripts/observe_pronunciation.py",
        )
    return FileResponse(path, media_type="audio/mpeg")
