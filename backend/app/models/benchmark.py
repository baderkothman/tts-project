"""Benchmark models and statistics."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArabicSample(BaseModel):
    """A reusable labelled test text.

    ``expected_contains`` lets SC-003 be asserted per sample rather than judged
    by eye (FR-038a).
    """

    id: str
    text: str
    category: str
    locale: str = "ar-SA"
    description: str = ""
    expected_behavior: str | None = None
    expected_contains: list[str] = Field(default_factory=list)
    expected_absent: list[str] = Field(default_factory=list)


class StageStats(BaseModel):
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    count: int


class BenchmarkResult(BaseModel):
    sample_id: str
    provider: str
    voice_id: str
    repetitions: int
    stages: dict[str, StageStats] = Field(default_factory=dict)
    failures: int = 0
    real_time_factor: StageStats | None = None


class BenchmarkRun(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    provider: str
    voice_id: str | None = None
    sample_set: list[str] = Field(default_factory=list)
    repetitions: int = 5
    warmup_discarded: bool = True
    environment: dict[str, str] = Field(default_factory=dict)
    results: list[BenchmarkResult] = Field(default_factory=list)
