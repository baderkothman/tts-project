"""Repeatable Arabic TTS benchmarking (FR-035-FR-037, research R7).

Warm-up is discarded (connection setup cost, not synthesis cost — verified
locally: a cold TTFA of ~2.5s vs steady-state well under that) and the fact
is recorded in the run rather than silently hidden. P95 uses nearest-rank,
not interpolation, since interpolating a percentile over ~5 repetitions
implies precision the sample size does not support.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from backend.app.data.samples import SAMPLES
from backend.app.models.benchmark import ArabicSample, BenchmarkResult, BenchmarkRun, StageStats
from backend.app.models.voice import EmotionStyle
from backend.app.providers.base import ProviderRequest
from backend.app.providers.base import TTSProvider
from backend.app.services.latency import LatencyTrace
from backend.app.services.voice_router import resolve_voice
from backend.app.text_processing.pipeline import process_text

BENCHMARKS_DIR = Path(__file__).resolve().parents[3] / "benchmarks"


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = math.ceil(0.95 * len(ordered)) - 1
    return ordered[max(0, min(rank, len(ordered) - 1))]


def _stage_stats(values: list[float]) -> StageStats:
    return StageStats(
        min_ms=min(values),
        max_ms=max(values),
        mean_ms=statistics.mean(values),
        median_ms=statistics.median(values),
        p95_ms=_percentile_95(values),
        count=len(values),
    )


async def _synthesize_once(
    provider: TTSProvider, sample: ArabicSample, voice
) -> LatencyTrace:
    trace = LatencyTrace()
    processed = process_text(sample.text, locale=sample.locale, provider=provider.id)
    trace.mark("T2")
    request = ProviderRequest(
        text=processed.processed, voice=voice, emotion=EmotionStyle.NEUTRAL
    )
    trace.mark("T3")
    first = True
    async for chunk in provider.stream(request):
        if first:
            trace.mark("T4")
            first = False
        trace.audio_bytes += len(chunk)
    trace.mark("T5")
    trace.mark("T7")
    return trace


async def run_benchmark(
    provider: TTSProvider,
    *,
    sample_ids: list[str] | None = None,
    repetitions: int = 5,
    warmup: bool = True,
) -> BenchmarkRun:
    samples = [s for s in SAMPLES if not sample_ids or s.id in sample_ids]
    voices = await provider.get_voices()
    default_voice = resolve_voice(provider, voices)

    run = BenchmarkRun(
        run_id=str(uuid.uuid4())[:8],
        started_at=datetime.now(UTC),
        provider=provider.id,
        voice_id=default_voice.id,
        sample_set=[s.id for s in samples],
        repetitions=repetitions,
        warmup_discarded=warmup,
        environment={"python": "3.12"},
    )

    for sample in samples:
        stage_values: dict[str, list[float]] = {
            "preprocessing_ms": [], "provider_ttfa_ms": [], "backend_ttfa_ms": [],
            "total_generation_ms": [],
        }
        rtf_values: list[float] = []
        failures = 0

        if warmup:
            try:
                await _synthesize_once(provider, sample, default_voice)
            except Exception:
                pass  # warm-up failures don't count against the measured run

        for _ in range(repetitions):
            try:
                trace = await _synthesize_once(provider, sample, default_voice)
                report = trace.report()
                for key in stage_values:
                    val = getattr(report, key)
                    if val is not None:
                        stage_values[key].append(val)
                if report.real_time_factor is not None:
                    rtf_values.append(report.real_time_factor)
            except Exception:
                failures += 1

        stages = {k: _stage_stats(v) for k, v in stage_values.items() if v}
        run.results.append(
            BenchmarkResult(
                sample_id=sample.id,
                provider=provider.id,
                voice_id=default_voice.id,
                repetitions=repetitions,
                stages=stages,
                failures=failures,
                real_time_factor=_stage_stats(rtf_values) if rtf_values else None,
            )
        )

    run.finished_at = datetime.now(UTC)
    return run


def persist_run(run: BenchmarkRun) -> dict[str, Path]:
    BENCHMARKS_DIR.mkdir(exist_ok=True)
    provider_file = BENCHMARKS_DIR / f"{run.provider}.json"
    results_file = BENCHMARKS_DIR / "results.json"
    comparison_file = BENCHMARKS_DIR / "comparison.csv"

    provider_file.write_text(run.model_dump_json(indent=2), encoding="utf-8")

    all_runs = []
    if results_file.exists():
        try:
            all_runs = json.loads(results_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            all_runs = []
    all_runs.append(json.loads(run.model_dump_json()))
    results_file.write_text(json.dumps(all_runs, indent=2), encoding="utf-8")

    file_exists = comparison_file.exists()
    with comparison_file.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["run_id", "provider", "voice_id", "sample_id", "stage",
                 "min_ms", "max_ms", "mean_ms", "median_ms", "p95_ms", "count", "timestamp"]
            )
        for result in run.results:
            for stage_name, stats in result.stages.items():
                writer.writerow([
                    run.run_id, run.provider, result.voice_id, result.sample_id, stage_name,
                    f"{stats.min_ms:.2f}", f"{stats.max_ms:.2f}", f"{stats.mean_ms:.2f}",
                    f"{stats.median_ms:.2f}", f"{stats.p95_ms:.2f}", stats.count,
                    run.started_at.isoformat(),
                ])

    return {"provider": provider_file, "results": results_file, "comparison": comparison_file}


async def _cli() -> None:
    import argparse

    from backend.app.providers.registry import get_registry

    parser = argparse.ArgumentParser(description="Run the Arabic TTS benchmark")
    parser.add_argument("--provider", default="edge")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--sample-ids", nargs="*", default=None)
    args = parser.parse_args()

    provider = get_registry().get(args.provider)
    if provider is None:
        raise SystemExit(f"unknown provider '{args.provider}'")

    run = await run_benchmark(provider, sample_ids=args.sample_ids, repetitions=args.repetitions)
    paths = persist_run(run)
    print(f"Benchmark complete: {run.run_id}")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_cli())
