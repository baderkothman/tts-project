"""Dialect classifier degradation tests (FR-057, T136)."""

from __future__ import annotations

import httpx
import pytest

from backend.app.text_processing.huggingface import dialect_classifier

_RealAsyncClient = httpx.AsyncClient


def _patch(monkeypatch, handler) -> None:
    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("backend.app.text_processing.huggingface.dialect_classifier.httpx.AsyncClient", factory)


@pytest.mark.asyncio
async def test_no_token_degrades_without_network_call():
    result = await dialect_classifier.classify("مرحبا", hf_token=None)
    assert result.label is None
    assert result.unavailable_reason == "HF_TOKEN not configured"


@pytest.mark.asyncio
async def test_cold_start_503_degrades_gracefully(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "loading"})

    _patch(monkeypatch, handler)
    result = await dialect_classifier.classify("مرحبا", hf_token="fake")
    assert result.label is None
    assert "cold-starting" in result.unavailable_reason


@pytest.mark.asyncio
async def test_successful_classification_maps_label_to_profile(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"label": "LEV", "score": 0.87}, {"label": "MSA", "score": 0.13}])

    _patch(monkeypatch, handler)
    result = await dialect_classifier.classify("شو رأيك", hf_token="fake")
    assert result.label == "LEV"
    assert result.resolved_dialect == "levantine"
    assert result.confidence == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_unrecognized_response_shape_degrades(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _patch(monkeypatch, handler)
    result = await dialect_classifier.classify("مرحبا", hf_token="fake")
    assert result.label is None
    assert result.unavailable_reason is not None
