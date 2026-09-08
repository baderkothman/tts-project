# Performance Benchmarks — real measured latency and TTFA

Every number below comes from `scripts/benchmark_tts.py` calling the real running backend (`oddadmix/lahgtna-omnivoice-v2`, run locally) 3 times per sample per endpoint — raw results in `docs/benchmark_results.json`. Nothing here is estimated.

## Whole-clip latency (`/api/tts`) vs. time-to-first-audio (`/api/tts/stream`)

`/api/tts` returns the complete clip in one response — its 'latency' *is* its time-to-first-audio, because there is no earlier moment any audio exists. `/api/tts/stream` (sentence-chunked, see `sentence_splitter.py`) can return the first sentence's audio while the rest of the text is still synthesizing — that's the number that matters for a real-time conversational avatar, where the user needs to hear *something* quickly, not wait for the entire reply.

| Sample | Chars | Chunks | `/api/tts` total (median) | Stream TTFA (median) | Stream total (median) | TTFA improvement |
|---|---|---|---|---|---|---|
| `msa_01` | 71 | 1 | 4768ms | 4760ms | 4762ms | 0% faster to first sound |
| `dialect_saudi_01` | 61 | 2 | 5653ms | 1938ms | 6414ms | 66% faster to first sound |
| `difficult_names_01` | 71 | 1 | 7202ms | 7191ms | 7193ms | 0% faster to first sound |
| `mixed_content_01` | 115 | 2 | 10736ms | 1787ms | 14250ms | 83% faster to first sound |

## Per-sample min/median/max (ms), across all repeats

| Sample | `/api/tts` [min/median/max] | Stream TTFA [min/median/max] | Stream total [min/median/max] |
|---|---|---|---|
| `msa_01` | 4767 / 4768 / 5442 | 4758 / 4760 / 4776 | 4759 / 4762 / 4778 |
| `dialect_saudi_01` | 5645 / 5653 / 7833 | 1938 / 1938 / 2064 | 6381 / 6414 / 6479 |
| `difficult_names_01` | 7200 / 7202 / 9616 | 7189 / 7191 / 7192 | 7191 / 7193 / 7194 |
| `mixed_content_01` | 10701 / 10736 / 11551 | 1475 / 1787 / 1913 | 12149 / 14250 / 14828 |

## What this does and doesn't prove

- Streaming's TTFA win scales with how many sentences the text splits into — a single-sentence input has one chunk, so its stream TTFA is close to its non-streaming total (no win, small SSE/HTTP overhead if anything). The win is real for multi-sentence replies, which is the actual shape of a conversational answer.
- This is still per-sentence batch generation, not token-level streaming — `OmniVoice.generate()` has no incremental API (see `sentence_splitter.py`'s docstring). A production system wanting sub-sentence TTFA needs a model that exposes real streaming generation, not just faster sentence chunking.
- Measured on Apple Silicon (MPS) with the process warm (model already loaded, first request of the process excluded) — cold-start load time is a separate, already-documented number in the README (~152s to load Lahgtna's weights on first run).
- No concurrent-request load testing — every measurement here is one request at a time against a single process; production concurrency behavior (see `docs/PRODUCTION_ARCHITECTURE.md`) is not what this script measures.