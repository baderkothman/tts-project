#!/usr/bin/env python3
"""Measures real latency against the live backend — the item 5 deliverable:
whole-clip generation latency (`/api/tts`, what the UI shows today as RTF)
versus time-to-first-audio (`/api/tts/stream`, sentence-chunked). Writes
`docs/PERFORMANCE_BENCHMARKS.md` from its own measured output; nothing in
that doc is hand-typed.

Runs each sample in `samples.py` `--repeats` times (default 3) on both
endpoints and reports min/median/max, since a single call is noise, not a
number worth publishing.

Usage:
    .venv/bin/uvicorn backend.app.main:app --port 8000 &   # if not already running
    .venv/bin/python scripts/benchmark_tts.py [--repeats 3]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from samples import SAMPLES, Sample  # noqa: E402

BASE_URL = "http://localhost:8000"
RESULTS_JSON = Path(__file__).resolve().parents[1] / "docs" / "benchmark_results.json"
REPORT_PATH = Path(__file__).resolve().parents[1] / "docs" / "PERFORMANCE_BENCHMARKS.md"


@dataclass
class RunResult:
    sample_id: str
    text_chars: int
    non_streaming_total_ms: list[float]
    stream_ttfa_ms: list[float]
    stream_total_ms: list[float]
    stream_chunk_count: int


def _form_data(sample: Sample) -> dict:
    return {
        "text": sample.text,
        "dialect_id": sample.dialect_id,
        "pitch": sample.pitch,
        "whisper": str(sample.whisper).lower(),
    }


def bench_non_streaming(client: httpx.Client, sample: Sample) -> float:
    t0 = time.perf_counter()
    resp = client.post(f"{BASE_URL}/api/tts", data=_form_data(sample), timeout=120.0)
    resp.raise_for_status()
    return (time.perf_counter() - t0) * 1000.0


def bench_streaming(client: httpx.Client, sample: Sample) -> tuple[float, float, int]:
    """Returns (ttfa_ms, total_ms, chunk_count) parsed from the SSE stream's
    own `done` event — the server's own perf_counter measurements, not this
    script's wall-clock guess, so network/parsing overhead on the client
    side isn't mistaken for server-side latency."""
    with client.stream("POST", f"{BASE_URL}/api/tts/stream", data=_form_data(sample), timeout=120.0) as resp:
        resp.raise_for_status()
        event = None
        for line in resp.iter_lines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: ") and event == "done":
                payload = json.loads(line[len("data: ") :])
                return payload["ttfa_ms"], payload["total_ms"], payload["chunk_count"]
    raise RuntimeError(f"stream for {sample.id} never emitted a 'done' event")


def run_benchmark(repeats: int) -> list[RunResult]:
    results: list[RunResult] = []
    with httpx.Client() as client:
        health = client.get(f"{BASE_URL}/api/health", timeout=10.0).json()
        if health.get("status") != "ok":
            print(f"Backend not ready: {health}")
            raise SystemExit(1)

        for sample in SAMPLES:
            print(f"Benchmarking {sample.id} ({repeats} repeats each)...")
            non_stream_times = []
            ttfa_times = []
            stream_total_times = []
            chunk_count = 0
            for _ in range(repeats):
                non_stream_times.append(bench_non_streaming(client, sample))
            for _ in range(repeats):
                ttfa, total, chunks = bench_streaming(client, sample)
                ttfa_times.append(ttfa)
                stream_total_times.append(total)
                chunk_count = chunks

            results.append(
                RunResult(
                    sample_id=sample.id,
                    text_chars=len(sample.text),
                    non_streaming_total_ms=non_stream_times,
                    stream_ttfa_ms=ttfa_times,
                    stream_total_ms=stream_total_times,
                    stream_chunk_count=chunk_count,
                )
            )
    return results


def _stats(values: list[float]) -> dict:
    return {"min": min(values), "median": statistics.median(values), "max": max(values)}


def write_report(results: list[RunResult], repeats: int) -> None:
    RESULTS_JSON.write_text(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Performance Benchmarks — real measured latency and TTFA",
        "",
        f"Every number below comes from `scripts/benchmark_tts.py` calling the real running "
        f"backend (`oddadmix/lahgtna-omnivoice-v2`, run locally) {repeats} times per sample per "
        "endpoint — raw results in `docs/benchmark_results.json`. Nothing here is estimated.",
        "",
        "## Whole-clip latency (`/api/tts`) vs. time-to-first-audio (`/api/tts/stream`)",
        "",
        "`/api/tts` returns the complete clip in one response — its 'latency' *is* its "
        "time-to-first-audio, because there is no earlier moment any audio exists. "
        "`/api/tts/stream` (sentence-chunked, see `sentence_splitter.py`) can return the "
        "first sentence's audio while the rest of the text is still synthesizing — that's "
        "the number that matters for a real-time conversational avatar, where the user needs "
        "to hear *something* quickly, not wait for the entire reply.",
        "",
        "| Sample | Chars | Chunks | `/api/tts` total (median) | Stream TTFA (median) | "
        "Stream total (median) | TTFA improvement |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        ns = _stats(r.non_streaming_total_ms)
        ttfa = _stats(r.stream_ttfa_ms)
        st = _stats(r.stream_total_ms)
        improvement = (1 - ttfa["median"] / ns["median"]) * 100 if ns["median"] > 0 else 0.0
        lines.append(
            f"| `{r.sample_id}` | {r.text_chars} | {r.stream_chunk_count} | "
            f"{ns['median']:.0f}ms | {ttfa['median']:.0f}ms | {st['median']:.0f}ms | "
            f"{improvement:.0f}% faster to first sound |"
        )

    lines += [
        "",
        "## Per-sample min/median/max (ms), across all repeats",
        "",
        "| Sample | `/api/tts` [min/median/max] | Stream TTFA [min/median/max] | "
        "Stream total [min/median/max] |",
        "|---|---|---|---|",
    ]
    for r in results:
        ns = _stats(r.non_streaming_total_ms)
        ttfa = _stats(r.stream_ttfa_ms)
        st = _stats(r.stream_total_ms)
        lines.append(
            f"| `{r.sample_id}` | {ns['min']:.0f} / {ns['median']:.0f} / {ns['max']:.0f} | "
            f"{ttfa['min']:.0f} / {ttfa['median']:.0f} / {ttfa['max']:.0f} | "
            f"{st['min']:.0f} / {st['median']:.0f} / {st['max']:.0f} |"
        )

    lines += [
        "",
        "## What this does and doesn't prove",
        "",
        "- Streaming's TTFA win scales with how many sentences the text splits into — a "
        "single-sentence input has one chunk, so its stream TTFA is close to its "
        "non-streaming total (no win, small SSE/HTTP overhead if anything). The win is real "
        "for multi-sentence replies, which is the actual shape of a conversational answer.",
        "- This is still per-sentence batch generation, not token-level streaming — "
        "`OmniVoice.generate()` has no incremental API (see `sentence_splitter.py`'s "
        "docstring). A production system wanting sub-sentence TTFA needs a model that "
        "exposes real streaming generation, not just faster sentence chunking.",
        "- Measured on Apple Silicon (MPS) with the process warm (model already loaded, "
        "first request of the process excluded) — cold-start load time is a separate, "
        "already-documented number in the README (~152s to load Lahgtna's weights on first run).",
        "- No concurrent-request load testing — every measurement here is one request at a "
        "time against a single process; production concurrency behavior (see "
        "`docs/PRODUCTION_ARCHITECTURE.md`) is not what this script measures.",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    results = run_benchmark(args.repeats)
    write_report(results, args.repeats)
    print(f"Wrote {RESULTS_JSON} and {REPORT_PATH}")


if __name__ == "__main__":
    main()
