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

---

## Groq (Orpheus Arabic — Saudi dialect)

**Run**: `315bd286` | **Provider**: groq | **Voice**: `groq:ar-SA-abdullah`
**Repetitions**: 3 per sample (+1 discarded warm-up) | **Environment**: same
network path as the Edge run above; Groq's REST endpoint rather than a
persistent connection.

| Sample | Preprocessing (ms) | Provider TTFA mean (ms) | Provider TTFA P95 (ms) | Total generation (ms) | Failures |
|---|---:|---:|---:|---:|---:|
| msa-1 | 0.29 | 781.4 | 809.7 | 781.8 | 0/3 |
| msa-2 | 0.38 | 864.1 | 938.3 | 864.5 | 0/3 |
| dialect-egyptian-1 | 0.35 | 4817.2 | 6924.4 | 4817.6 | 0/3 |
| dialect-gulf-1 | 0.36 | 7007.1 | 7412.7 | 7007.5 | 0/3 |
| pronunciation-1 | 0.40 | 6912.9 | 6937.8 | 6913.4 | 0/3 |
| numbers-1 | 0.53 | 7876.3 | 8061.0 | 7876.9 | 0/3 |
| dates-1 | 0.43 | 7745.1 | 7952.6 | 7745.6 | 0/3 |
| currencies-1 | 0.63 | 7476.9 | 7680.8 | 7477.5 | 0/3 |
| abbreviations-1 | — | — | — | — | 3/3 |
| code-switching-1 | — | — | — | — | 3/3 |
| emotion-1 | — | — | — | — | 3/3 |

**The real, unfiltered story here — not smoothed over**: "Provider TTFA" for
Groq is not synthesis latency. `capabilities().streaming` is `False` for this
adapter (research R1 — no incremental streaming is documented for the Arabic
model), so T4 (first byte) and T7 (complete) land together, and the reported
number is essentially total round-trip time for one REST call. What actually
produced the 780ms → 7–8s climb across this table, and the total failure of
the last three samples, is a **hard rate limit discovered only by exceeding
it live**: Groq returns `429` with `Retry-After` once 10 requests/minute is
exceeded on this model (on-demand tier) — not documented on the model's docs
page fetched during research. The adapter (`groq.py`) retries once,
honoring `Retry-After` (capped at 15s); the climbing TTFA in this table
**is that backoff wait being included in the measurement**, honestly, rather
than excluded to make the number look better. By `abbreviations-1` the
single retry was no longer enough — a second consecutive 429 still raises
`ProviderError(kind="rate_limit")`, which is why the last three samples show
3/3 failures rather than a number.

**What this means for the "real-time avatar" evaluation**: Groq's Orpheus
Arabic model is not a viable *high-throughput* or *low-latency* streaming
choice today — it is a genuinely dialect-authentic **single-request**
synthesis path, well suited to on-demand generation (e.g., a chatbot's
occasional Arabic reply) but not to the burst pattern a benchmark, or a busy
conversational avatar, produces. This is a real, measured production
consideration (docs/PRODUCTION_ARCHITECTURE.md), not a code defect —
repeated attempts to re-run this benchmark immediately afterward (runs
`f708b20a`, `d5255052`, `edd71936` in `benchmarks/results.json`) failed
outright for the same reason: the rate-limit window does not clear quickly
under repeated benchmark-style load.

Reproduce with `GROQ_API_KEY` set:

```bash
.venv/bin/python -m backend.app.services.benchmark_service --provider groq --repetitions 1
```

Expect some 429s if run in quick succession after a prior benchmark; space
runs at least a minute apart, or expect a subset of samples to fail exactly
as documented above — that failure is the finding, not a bug to hide.

## ElevenLabs

**Run**: `573aa958` | **Provider**: elevenlabs | **Voice**: `elevenlabs:sarah`
**Repetitions**: 3 per sample (+1 discarded warm-up) | **Environment**: same
network path as the runs above; ElevenLabs' SSE streaming endpoint.

| Sample | Preprocessing (ms) | Provider TTFA mean (ms) | Provider TTFA P95 (ms) | Total generation (ms) | Failures |
|---|---:|---:|---:|---:|---:|
| msa-1 | 0.38 | 531.1 | 552.6 | 761.1 | 0/3 |
| msa-2 | 0.28 | 553.1 | 611.2 | 823.4 | 0/3 |
| dialect-egyptian-1 | 0.26 | 522.5 | 570.8 | 710.4 | 0/3 |
| dialect-gulf-1 | 0.32 | 535.4 | 547.5 | 740.2 | 0/3 |
| pronunciation-1 | 0.34 | 565.5 | 606.9 | 778.9 | 0/3 |
| numbers-1 | 0.51 | 520.1 | 531.8 | 952.1 | 0/3 |
| dates-1 | 0.47 | 494.4 | 522.1 | 923.5 | 0/3 |
| currencies-1 | 0.48 | 563.7 | 613.1 | 905.5 | 0/3 |
| abbreviations-1 | 0.39 | 522.2 | 573.8 | 821.3 | 0/3 |
| code-switching-1 | 0.46 | 545.1 | 575.5 | 811.0 | 0/3 |
| emotion-1 | 0.29 | 696.5 | 864.2 | 882.5 | 0/3 |

**Zero failures** across all 11 samples × 3 repetitions = 33 live synthesis calls — this run
was clean on the first attempt, unlike Groq's above. Provider TTFA (~500–700ms mean) is
genuinely lower than both Edge (~1.3–1.7s) and Groq (~780–940ms before its rate limit hit),
and this IS real streaming: `capabilities().streaming` is `True` and confirmed live —
T4 (first byte) lands well before T7 (complete), unlike Groq's single-shot round trip.

**Getting here required fixing two real problems first, not just configuring a key** — see
`docs/TTS_EVALUATION.md` and `specs/001-arabic-tts-prototype/tasks.md` Phase 13:
1. The configured API key was scoped without `voices_read` permission, so the account's own
   voice library couldn't be queried at all (401) until that permission was granted.
2. Both originally-catalogued voices (Rachel, Adam) were assumed usable from vendor
   documentation; live testing found Rachel is a public "Voice Library" voice the free tier
   cannot call via the API (402), while Adam happened to already be in this account's own
   library and worked. Rachel was replaced with **Sarah**, one of the ~20 premade voices
   ElevenLabs provisions to every new account by default — confirmed live before adopting it,
   not assumed from a voice list.

Reproduce with `ELEVENLABS_API_KEY` set:

```bash
.venv/bin/python -m backend.app.services.benchmark_service --provider elevenlabs --repetitions 3
```
