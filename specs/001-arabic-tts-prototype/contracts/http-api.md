# Contract: HTTP API

**Feature**: `001-arabic-tts-prototype` | Base: `http://127.0.0.1:8000`

All request bodies are Pydantic-validated; a violation returns `422` with field detail.
No endpoint ever returns a credential value (FR-039). No endpoint logs request text (FR-040).

---

## `POST /api/tts` — synthesize complete audio

Non-streaming path (FR-030). Body: `TTSRequest`. Returns `200` with `TTSResponse`
(`audio_base64` + `processed_text` + `voice` + `latency`).

Errors: `422` validation; `400` unsupported locale/voice/style — body names valid
alternatives (FR-026); `503` no provider available, naming what would enable each (FR-024).

## `POST /api/tts/stream` — synthesize with streaming

Primary path (FR-029). Body: `TTSRequest`. Returns `200`, `Content-Type: audio/mpeg`,
`Transfer-Encoding: chunked`.

**Contract**: the first chunk MUST be written to the response as soon as the provider
yields it — the handler MUST NOT accumulate the full audio first. This is the property
SC-002 tests.

Metadata that cannot ride in an audio body is returned as headers:

| Header | Meaning |
|--------|---------|
| `X-TTS-Provider` | Provider that served the request |
| `X-TTS-Voice` | Voice id used (FR-025) |
| `X-TTS-Used-Fallback` | `true`/`false` (FR-033) |
| `X-TTS-Emotion-Native` | `false` when prosody-approximated (FR-028) |
| `X-TTS-Preprocess-Ms` | Preprocessing duration |
| `X-TTS-Provider-TTFA-Ms` | Provider time-to-first-audio |

Because a stream's status is committed with the first byte, all validation and voice
resolution happen **before** any byte is written; a mid-stream provider failure that occurs
after bytes are sent terminates the stream rather than changing the status code, and the
client detects truncation. This asymmetry is why `X-TTS-*` headers are set up front.

## `POST /api/preview` — processed text without synthesis

Returns `ProcessedText` with per-stage diffs (FR-015, FR-016). No provider call, so it is
the cheapest way to test the pipeline and it works with zero credentials.

## `GET /api/providers`

Lists every provider with `status`, `capabilities`, `voice_count`, `unavailable_reason`.
Providers lacking credentials appear with `missing_credentials` — never omitted (FR-024).

## `GET /api/voices?provider=&locale=&dialect=`

Filtered voice catalogue (FR-023). `GET /api/locales` returns supported locales and the
dialect families they belong to.

## `GET /api/samples`

The Arabic evaluation sample set with categories and expected behaviour (FR-038).

## `POST /api/benchmark`

Body: `{provider, voice_id?, sample_ids?, repetitions=5, warmup=true}`.
Runs the benchmark, writes files under `benchmarks/`, returns a `BenchmarkRun`
with per-stage min/max/mean/median/P95 (FR-035–FR-037).

## `GET /api/pronunciation/demo`

Returns the recorded `PronunciationDemo` — original text, observed defect, desired
pronunciation, technique, and the provider/voice on which it was observed (FR-019).

## `GET /api/pronunciation/demo/audio?corrected=true|false`

Streams the before or after rendering of the same source text (FR-020).

## `GET /health`

`{"status": "ok", "providers_available": n}`.

## `GET /`

Serves the static demonstration page.

---

## Cross-cutting contract tests

| ID | Assertion | Requirement |
|----|-----------|-------------|
| AC-01 | Empty/whitespace text → 422 | FR-003 |
| AC-02 | Text > 5000 chars → 422 stating limit and actual length | FR-003 |
| AC-03 | Unsupported locale → 400 listing supported locales | FR-026 |
| AC-04 | Voice not owned by provider → 400 | FR-026 |
| AC-05 | Markup-like text is spoken literally, never interpreted | FR-041 |
| AC-06 | No response body or header contains a credential | FR-039 |
| AC-07 | Stream emits its first chunk before synthesis completes | FR-029, SC-002 |
| AC-08 | Primary failure → fallback served, `used_fallback` true | FR-033 |
| AC-09 | All providers unavailable → 503, service still running | FR-034 |
| AC-10 | Every synthesis response carries a complete `LatencyReport` | FR-031 |
