"""Benchmark endpoints (FR-035, FR-038)."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from backend.app.data.samples import SAMPLES
from backend.app.models.benchmark import ArabicSample, BenchmarkRun
from backend.app.providers.registry import get_registry
from backend.app.services.benchmark_service import persist_run, run_benchmark

router = APIRouter(prefix="/api", tags=["benchmark"])


class BenchmarkRequest(BaseModel):
    provider: str
    sample_ids: list[str] | None = None
    repetitions: int = 5
    warmup: bool = True


@router.get("/samples", response_model=list[ArabicSample])
async def list_samples() -> list[ArabicSample]:
    return SAMPLES


@router.post("/benchmark", response_model=BenchmarkRun)
async def benchmark(request: BenchmarkRequest) -> BenchmarkRun:
    provider = get_registry().get(request.provider)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"unknown provider '{request.provider}'")

    run = await run_benchmark(
        provider,
        sample_ids=request.sample_ids,
        repetitions=request.repetitions,
        warmup=request.warmup,
    )
    persist_run(run)
    return run
