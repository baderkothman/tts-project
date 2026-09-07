# Benchmark Results

**Real, executed output** — not projected figures. Reproduce with:

```bash
.venv/bin/python -m backend.app.services.benchmark_service --provider edge --repetitions 3
```

**Run**: `803bc381` | **Provider**: edge | **Voice**: `edge:ar-SA-female`
**Repetitions**: 3 per sample (+1 discarded warm-up) | **Environment**: this
implementation machine's network path to the Microsoft Edge endpoint — these
are NOT provider-intrinsic figures; a different network path will differ
(research R7, Constitution V).

## Per-sample results (mean)

| Sample | Preprocessing (ms) | Provider TTFA mean (ms) | Provider TTFA P95 (ms) | Total generation (ms) | Failures |
|---|---:|---:|---:|---:|---:|
| msa-1 | 0.33 | 1332.8 | 1454.5 | 1837.7 | 0 |
| msa-2 | 0.38 | 1411.2 | 1591.0 | 2193.8 | 0 |
| dialect-egyptian-1 | 0.42 | 1684.6 | 2267.9 | 2283.9 | 0 |
| dialect-gulf-1 | 0.43 | 1450.2 | 1557.4 | 2166.6 | 0 |
| pronunciation-1 | 0.33 | 1342.4 | 1385.6 | 1965.8 | 0 |
| numbers-1 | 0.56 | 1346.6 | 1382.3 | 2447.3 | 0 |
| dates-1 | 0.51 | 1303.1 | 1342.2 | 2099.0 | 0 |
| currencies-1 | 0.44 | 1691.0 | 2312.4 | 2335.0 | 0 |
| abbreviations-1 | 0.36 | 1463.2 | 1527.0 | 2107.2 | 0 |
| code-switching-1 | 0.52 | 1436.7 | 1549.0 | 2142.1 | 0 |
| emotion-1 | 0.38 | 1389.6 | 1537.8 | 1756.7 | 0 |

## What this shows

- **Preprocessing is never the bottleneck**: 0.33–0.56ms across every sample,
  far under the 50ms/500-char budget in SC-004 (also directly verified by
  `test_pipeline_performance.py`, which measures 20 repetitions on a 500-char
  passage).
- **TTFA is dominated by connection/network cost, not synthesis**: provider
  TTFA (~1.3–1.7s mean) is 55–75% of total generation time on this network
  path. This matches the cold-start probe from `research.md` R1 (2485ms cold
  TTFA) — first-connection cost is real and is not hidden by the warm-up
  discard (`warmup_discarded: true` is recorded in every run file).
- **Zero failures** across 11 samples × 3 repetitions = 33 live synthesis
  calls in this run.
- Full per-run JSON: `benchmarks/edge.json`, `benchmarks/results.json`.
  Flat CSV for spreadsheet comparison: `benchmarks/comparison.csv`.

## Honest limitation

Only the `edge` provider was benchmarked with live data — Azure and
ElevenLabs adapters are implemented and contract-tested, but no credentials
were available in this environment to produce comparable live numbers for
them (Assumptions, spec.md). Running
`python -m backend.app.services.benchmark_service --provider azure` with
`AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION` set will produce a directly
comparable `benchmarks/azure.json` against the identical sample set.
