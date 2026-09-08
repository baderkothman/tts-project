from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import tts as tts_module
from backend.app.services import diacritizer, text_preprocessor
from backend.app.services.fake_engine import FakeEngine
from backend.app.services.speech_pipeline import SpeechPipeline


@pytest.fixture(autouse=True)
def _no_real_diacritizer_model(monkeypatch):
    """Contract tests never load the real Fine-Tashkeel weights — a
    pass-through keeps /api/tts and /api/preprocess exercising real
    segmentation/orchestration logic without a model dependency."""
    monkeypatch.setattr(diacritizer, "diacritize", lambda text, *, dialect_id="msa": (text, False))
    text_preprocessor.preprocess.cache_clear()
    yield
    text_preprocessor.preprocess.cache_clear()


def make_client(engine: FakeEngine | None = None) -> TestClient:
    """A minimal app wired to a `FakeEngine` (via a real `SpeechPipeline`,
    so /api/tts and /api/preprocess exercise the real preprocessing
    pipeline) — never triggers the real `main.py` lifespan, so contract
    tests never touch model weights."""
    app = FastAPI()
    app.include_router(tts_module.router)
    eng = engine if engine is not None else FakeEngine()
    app.state.engine = eng
    app.state.pipeline = SpeechPipeline(eng)
    return TestClient(app)
