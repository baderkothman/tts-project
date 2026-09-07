from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import tts as tts_module
from backend.app.services.fake_engine import FakeEngine


def make_client(engine: FakeEngine | None = None) -> TestClient:
    """A minimal app wired to a `FakeEngine` — never triggers the real
    `main.py` lifespan, so contract tests never touch model weights."""
    app = FastAPI()
    app.include_router(tts_module.router)
    app.state.engine = engine if engine is not None else FakeEngine()
    return TestClient(app)
