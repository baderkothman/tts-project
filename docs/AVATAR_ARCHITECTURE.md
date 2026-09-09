# Talking Avatar — architecture

A working feature, not a proposal: everything described here is implemented, tested, and
was verified end to end through the real browser UI against the real backend — twice now.
First with `StubAvatarEngine` (portrait upload → real Lahgtna-generated Arabic audio →
real ffmpeg-encoded MP4 → playable in the browser, no AI). Then again after wiring in
**real AI lip sync**: `ReplicateAvatarEngine` (SadTalker, via Replicate's hosted API) is
now the active engine whenever `REPLICATE_API_TOKEN` is set — verified with a real
generation showing genuinely moving lips synced to this app's own real TTS audio, not a
procedural approximation. See `docs/AVATAR_MODEL_EVALUATION.md` for why SadTalker/Replicate
specifically (the "hardware reality" section, updated after MuseTalk/LatentSync turned out
to need a driving video rather than a single photo — a real mismatch found by checking the
actual input schema, not assumed), and `docs/AVATAR_SETUP.md` for how to run either engine.

## Target architecture (as built)

```text
React (AvatarStudioPanel)
       │  multipart POST /api/tts/avatar
       ▼
api/avatar.py ──────────────► AvatarJobManager (services/avatar_jobs.py)
  (validates portrait            │  in-process asyncio.Queue + worker tasks
   synchronously, returns             │
   202 + job_id immediately)         ├── SpeechPipeline.synthesize()  ─── the EXISTING,
       │                              │   (backend/app/services/           UNCHANGED TTS
       │  GET .../jobs/{id}           │    speech_pipeline.py)             pipeline
       │  GET .../jobs/{id}/events    │        │
       │  (SSE progress)              │        ▼ np.ndarray → WAV (tts_cache.py)
       ▼                              │
  AvatarJobResponse            └── AvatarEngine.generate()  ─── ReplicateAvatarEngine
  {status, progress,                   (services/avatar_engine.py)   (SadTalker, real AI —
   video_url, audio_url,                                             active when configured),
   duration, engine, ...}                                            else StubAvatarEngine
```

This *is* the brief's own target diagram, with every box a real module rather than a
placeholder name:

| Brief's box | Real module |
|---|---|
| Avatar API Layer | `backend/app/api/avatar.py` |
| Job Manager / Queue | `backend/app/services/avatar_jobs.py` (`AvatarJobManager`) |
| TTS Service | `backend/app/services/speech_pipeline.py` — **completely unmodified** by this feature |
| AvatarEngine Interface | `backend/app/services/avatar_engine.py` (`AvatarEngine` ABC) |
| Engine A / Engine B / Future Engine | `avatar_engines/replicate_engine.py` (active when `REPLICATE_API_TOKEN` is set — real AI lip sync), `avatar_engines/stub_engine.py` (active otherwise — free, non-AI fallback), `avatar_engines/hf_jobs_engine.py` (an alternative designed-but-not-implemented path, kept for a future self-hosted/custom-model option), `avatar_engines/fake_engine.py` (test double) |
| Video Processing / MP4 Storage | `avatar_engines/stub_engine.py`'s ffmpeg call + `.avatar_jobs/<job_id>/` |

**Lahgtna is not touched.** `avatar_jobs.py` imports `SpeechPipeline` and calls its public
`synthesize()` method exactly the way `api/tts.py` does — no new TTS code path, no
avatar-specific fork of preprocessing/diacritization/dialect handling. Swapping the avatar
engine later means changing which class `main.py` hands to `AvatarJobManager`
(`engine=StubAvatarEngine()` → `engine=HFJobsAvatarEngine()`), nothing else.

This also means the avatar audio step gets the automatic AI dialect rewrite for free, with
zero avatar-specific code: `SpeechPipeline.synthesize()` (unmodified) already calls
`dialect_rewriter.maybe_rewrite()` gated on `dialect_rewriter.is_configured()` — see
`README.md`'s "AI dialect rewrite" section — and `avatar_jobs.py` never needs to know that
happened. There is deliberately no `AvatarGenerationRequest` field for this (matching
`TTSRequest` — see `models/tts.py`'s module docstring): it's a server-wide, automatic
capability, not a per-request choice.

## The `AvatarEngine` abstraction

```python
class AvatarEngine(ABC):
    name: str
    async def generate(self, *, image_path, audio_path, emotion: EmotionConfig, options: AvatarOptions) -> AvatarResult: ...
```

One method. Portrait validation happens earlier (`services/portrait_validator.py`, before
a job even exists) and audio comes from the untouched TTS pipeline — by the time
`generate()` is called, both inputs are already known-good, so an engine's only job is
turning them into a video. `EmotionConfig` (`expression_strength`, `head_motion`,
`blink_rate`, `eye_motion`, `smile` — all 0..1, `blink_rate` a multiplier) is the
brief's own normalized representation, built from `data/emotions.py`'s six presets
(neutral/happy/sad/excited/calm/professional), each intensity capped at 0.6 or below —
a real, checked ceiling (`test_avatar_engine.py::test_no_preset_pushes_expression_past_the_brief_s_constrained_ceiling`),
not just a comment, per the brief's "constrained intensity, not exaggerated cartoon-like
motion" requirement.

**A documented, honest gap in this interface:** it carries no progress-callback or
cancellation-token parameter. That's why `AvatarJobStatus`'s per-state progress numbers
(`models/avatar.py::PROGRESS_BY_STATUS`) are coarse, not smooth — a real engine reporting
"40% of frames rendered" would need this signature extended, which is a real, deliberate
scope boundary for this pass, not an oversight.

## Job state machine

```
queued → preprocessing → generating_audio → preparing_avatar → generating_video → encoding → completed
                                                                                              ↘ failed
                                                                                              ↘ cancelled
```

Driven entirely by `AvatarJobManager._run_job()` — one function, one direction of state
transitions, no ad-hoc conditionals scattered across the API layer (matches AGENTS.md's
"Make state explicit and inspectable"). `encoding` is a real state in the contract even
though `StubAvatarEngine` folds actual encoding into the same `generate()` call as
`generating_video` (there's no separate frame-render-then-encode split for this engine) —
the state machine's contract doesn't change when the engine underneath does; a future
engine that genuinely separates those phases doesn't require a new state.

Progress is a coarse, honest number per state (`PROGRESS_BY_STATUS`), not a fabricated
smooth animation — see the abstraction gap noted above.

## Why in-process, not Celery/Redis

This repo has **no database, message broker, or multi-instance deployment story anywhere
today** — `config.py`/`main.py` confirm it directly: one process, in-memory TTS engine
state, no persistence layer. `AvatarJobManager` is therefore an `asyncio.Queue` plus a
handful of `asyncio.Task` workers *inside this one FastAPI process* — the same shape
`main.py`'s existing model-loading already uses (`asyncio.create_task` at startup).
Introducing Celery + Redis for a single-instance deployment would violate AGENTS.md §2
("do not add a framework... when deterministic code... meets the requirement") for no
present benefit.

**What a horizontally-scaled deployment would actually need to change:** the job table
(currently `dict[str, AvatarJob]` in `AvatarJobManager`) would need to move to a shared
store (Redis/Postgres) so any replica can serve `GET .../jobs/{id}`; the queue would need
to be a real broker so a job created on replica A can be picked up by a worker on replica
B; and `AvatarOptions.work_dir` (currently a local filesystem path) would need to become
object storage (S3-compatible) so a worker on a different machine than the API request
can read/write job artifacts. None of this is built — it's the concrete list of what
changes, matching `docs/PRODUCTION_ARCHITECTURE.md`'s own "migration path" table format
for the TTS side of this same repo.

## Cancellation — the honest scope

A **queued** job is cancelled outright — it never starts (`AvatarJobManager.cancel()`,
tested in `test_avatar_jobs.py::test_cancel_a_queued_job_is_immediate`). A job already
inside `AvatarEngine.generate()` **cannot be interrupted mid-flight**: `StubAvatarEngine`
runs real blocking work (a subprocess `ffmpeg` call) behind `asyncio.to_thread`, and
neither `Task.cancel()` nor `asyncio.wait_for`'s timeout can stop an already-running
thread-pool worker — only unblock the *coroutine waiting on it* once the thread finishes
on its own. So cancelling (or timing out) a job in `generating_video` is cooperative at
the stage boundary: the cancellation is recorded and reported to the client immediately,
but the abandoned engine call keeps running in the background until it finishes, at which
point its result is discarded (video file deleted, never surfaced) — verified directly in
`test_avatar_jobs.py::test_cancel_a_running_job_discards_its_result`.

This is a structural limitation of any *locally-run subprocess* engine, not a bug to fix
later with more code. `ReplicateAvatarEngine` is the concrete case this was written
for: Replicate predictions **can** be cancelled mid-flight for real (a genuine
`POST .../predictions/{id}/cancel` call, confirmed against the live API) — but nothing
wires it up yet, because `AvatarEngine.generate()`'s signature carries no cancellation
token to receive that signal through (see `avatar_engine.py`'s docstring). Threading one
through is the natural next step now that a real remote engine exists to use it, not a
speculative "maybe someday" — see `replicate_engine.py`'s own docstring for the same note.

## Storage lifecycle

```
.avatar_jobs/<job_id>/
  portrait.png       # re-encoded by portrait_validator.py — original upload bytes never stored
  ref_audio.bin       # only present for clone-mode requests
  output.mp4           # written directly by the active engine
.avatar_jobs/_tts_cache/
  <sha256>.wav          # content-addressed, outlives any one job (see Caching below)
```

Ephemeral scratch space, not meant to persist — `AvatarJobManager._cleanup_loop()` sweeps
terminal (completed/failed/cancelled) job directories older than
`Settings.avatar_job_retention_s` (24h default) every `avatar_cleanup_interval_s` (15min
default), and `cleanup_old_jobs()` is directly unit-tested
(`test_avatar_jobs.py::test_cleanup_removes_old_terminal_jobs_but_not_recent_ones`). No
Railway Volume is needed for this directory the way `HF_HOME` needs one for model
weights (`DEPLOY.md`) — losing it on a redeploy is fine by design.

**Safe filenames, always.** Every path under a job directory is a fixed name
(`portrait.png`, `output.mp4`, `ref_audio.bin`) or the job's own `uuid4().hex` — never
derived from user input, never containing a path separator a client could control. No
path-traversal surface exists in this feature.

## Caching

`services/tts_cache.py` — a content-addressed disk cache (`sha256` of
text+mode+dialect+gender+pitch+ref_text+speed+quality+guidance_scale+model_repo_id,
plus reference-audio bytes when cloning) scoped to the avatar pipeline only. The existing
standalone `POST /api/tts` is **untouched** — every call there still always regenerates,
exactly as before this feature existed.

`avatar_jobs.py::_synthesize_audio` computes the cache key from the raw `TTSRequest`
*before* calling `SpeechPipeline.synthesize()` — so the key is built from the raw, typed
text, not the AI-rewritten one (there is no separate rewrite step in `avatar_jobs.py` to
build a key from; the rewrite happens entirely inside `synthesize()`, same as `/api/tts`).
This is a deliberate, not incidental, cost win: two jobs with identical raw
text/dialect/voice fields are the same request as far as this cache is concerned, and a
cache hit means `synthesize()` — and therefore the OpenAI rewrite call inside it — never
runs at all for the second job. See `cache_key()`'s own docstring for the full reasoning.
Folding in `model_repo_id` means a future model upgrade can never serve stale audio from a
different model under the same key.

Video output is **not cached** — it additionally depends on the portrait, emotion, and
engine/model version, none of which repeats meaningfully across requests the way
identical text/voice can (a user regenerating with the same text after tweaking emotion
should get a genuinely different video).

## Security

- **File type/MIME/size validation** for both the portrait (`portrait_validator.py`:
  PNG/JPEG/WebP, 8MB cap) and reference audio (reuses `Settings.allowed_reference_audio_types`
  /`max_reference_audio_bytes`, identical rules to the existing `/api/tts` clone mode).
- **Decompression-bomb guard**: portrait dimension checks run *before* the full-pixel
  decode (`.convert("RGB")`), not after — a small, well-compressed file declaring an
  enormous pixel grid is rejected before it can allocate that memory. Verified directly:
  `test_portrait_validator.py::test_rejects_resolution_too_high_without_fully_decoding`
  makes a full decode raise if the check ordering ever regresses.
- **No shell interpolation, ever.** `StubAvatarEngine`'s `ffmpeg` call is
  `subprocess.Popen([...])` with a literal argument list — no `shell=True`, no string
  formatting of user input into a command line. User text never reaches the ffmpeg
  invocation at all (only file paths this app's own code constructed).
- **Safe filenames / no user-controlled paths** — see Storage lifecycle above.
- **Job/concurrency limits** — `Settings.avatar_max_concurrent_jobs` (1 by default) and
  `avatar_max_queued_jobs` (10) bound resource use; exceeding the queue cap raises
  `AvatarJobLimitError` → HTTP 429 (`test_api_avatar.py::test_job_limit_returns_429`).

**What is honestly not implemented, and why:** rate limiting and per-user authorization.
This app has **no authentication or user model anywhere** — verified directly, not
assumed (no session, no auth middleware in `main.py` or any router, old or new). `job_id`
(a random `uuid4().hex`) is the de facto access token for a job's media, exactly as it
would remain the only thing gating access even with auth bolted on later — but nothing
today checks that the caller fetching a job is the one who created it, beyond "do you
know the job_id". Adding real rate limiting/authorization is a whole-app change (this
feature would be the first thing to need it, not the natural place to invent an
auth system for the rest of the app). Flagged here, not silently shipped as if solved.

## Observability

`AvatarJob` carries `created_at`/`updated_at`/`processing_time_s`, and every failure path
sets a typed `(error_kind, error_message)` pair — the same `(kind, message)` shape
`InferenceError`/`DialectRewriteError` already use, now extended to `AvatarEngineError`
and `PortraitValidationError` (`api/avatar.py`'s `_ERROR_STATUS` table maps all of them to
HTTP status codes in one place, mirroring `api/tts.py`'s own `_ERROR_STATUS` convention).
`avatar_jobs.py`'s `logger.exception(...)` on the last-resort `except Exception` guard
logs a real traceback server-side without ever putting internal detail in the client-facing
`error_message`. **Not implemented**: structured per-stage latency logging (audio-gen time
vs. video-gen time vs. encoding time broken out) and any metrics/dashboard — `processing_time_s`
is currently one aggregate number, not a per-stage breakdown. A real next step, not built
this pass.

## Open questions (deliberately left for a human decision)

- **Cost/quota policy for `ReplicateAvatarEngine`.** Every generation is a real, metered
  charge (~$0.09–0.15/generation, confirmed against actual billed predictions while
  building this) against this server's own Replicate account — there is currently **no
  per-user quota or cost cap on top of** `avatar_max_concurrent_jobs`/`avatar_max_queued_jobs`
  (those bound *concurrency*, not *spend*). A public-facing deployment needs a real
  per-user or global spend cap before this is safe to expose without limit — a business
  decision (who pays, what the cap is) this codebase can't make on its own. Until that
  exists, treat `REPLICATE_API_TOKEN` as something to set only on a deployment you
  control access to.
- **Pose/full-body support** (brief's Phase 5). `StubAvatarEngine` and the concept it's
  standing in for are head/face-only by design — most Phase 5 poses assume limbs a
  portrait-photo-driven avatar doesn't have without a fundamentally different input
  (a full-body reference video or 3D model), which is a different feature, not an
  extension of this one.
- **Blink/eye-motion for a real engine.** `StubAvatarEngine` explicitly skips these
  (no eye landmarks available without a real model) — MuseTalk itself won't add them
  either (it only touches the mouth region), so the "combine specialized models"
  question from `docs/AVATAR_MODEL_EVALUATION.md` becomes concrete here: something
  landmark-aware (a lightweight face-landmark model, cheap and CPU-viable, distinct from
  MuseTalk itself) would need to sit alongside MuseTalk for real blinking/gaze.

## Future expansion — extension points already in place, nothing built

Per the brief's own "avoid premature implementation" principle: these are real hooks that
exist *because* of decisions already made above, not built-ahead speculative code.

- **Full-body avatars / gesture generation** — a new `AvatarOptions` field plus a new
  engine implementation; the API/job-manager contract doesn't change.
- **Streaming lip sync / real-time conversation** — `AvatarEngine.generate()` is
  currently request-response; a streaming variant would be a second abstract method
  (`generate_stream()`) engines opt into, following this project's own
  `SpeechPipeline.synthesize()` vs `synthesize_stream()` precedent exactly.
- **Avatar library / personalization** — `portrait_validator.ValidatedPortrait` already
  separates "a validated, normalized portrait" from "a job" — persisting validated
  portraits keyed by a future user id, instead of only inside one job's directory, is an
  additive change to `avatar_jobs.create_job()`, not a redesign.
- **Multilingual/English voices** — already inherited for free: `AvatarGenerationRequest`
  reuses this app's real `dialect_id`/`gender`/`pitch` fields verbatim, and the audio step
  goes through the *same* `SpeechPipeline` every other feature in this app uses, mixed-language
  handling included.
