"""Shared pytest fixtures. Fully offline — no provider credentials required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.fake import FakeProvider


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()
