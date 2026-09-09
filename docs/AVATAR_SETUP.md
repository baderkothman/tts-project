# Talking Avatar — setup

See `docs/AVATAR_ARCHITECTURE.md` for how this works and `docs/AVATAR_MODEL_EVALUATION.md`
for why the active engine is a real, honest placeholder rather than a GPU model. This
document is just: how to get it running.

## System dependencies

Beyond this repo's existing setup (`README.md`'s own "Setup" section — `espeak-ng`, the
Python venv, `npm install`), the Talking Avatar feature needs one more system binary:

```bash
brew install ffmpeg   # macOS
apt install ffmpeg    # Debian/Ubuntu
```

Already added to `Dockerfile`'s apt-get line for deployment — nothing extra needed there.

No separate face-detection model download is needed: `opencv-python-headless` (already a
Python dependency, installed via the same `uv pip install -e ".[dev]"` this repo's setup
already runs) bundles the Haar cascade `portrait_validator.py` uses.

**One real, verified gotcha, worth reading before "helpfully" bumping this dependency:**
`opencv-python-headless` is pinned `<5` in `pyproject.toml` for a *confirmed*, not assumed,
reason — installing 5.0.0 in this environment and checking directly showed its `cv2/data/`
directory is **empty**; `cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'`
does not exist on disk, so `_detect_faces()` would raise at the *first real request*, not
at import time. 4.14.0 (currently pinned) still bundles every cascade file exactly as
historically documented. Re-verify with a real install-and-check before ever loosening
this pin, the same way it was discovered here — don't just trust the version number.

## Environment variables

All optional — sensible repo-local defaults exist for every one (`config.py`'s
`avatar_storage_dir_override` etc. mirror the same "unset means repo-local, not scattered
outside the checkout" pattern `hf_home`/`HF_HOME` already use):

| Variable | Default | What it controls |
|---|---|---|
| `AVATAR_STORAGE_DIR_OVERRIDE` | `.avatar_jobs/` (repo-local) | Where job artifacts (portrait/audio/video) are written |
| `MAX_PORTRAIT_BYTES` | `8388608` (8MB) | Portrait upload size cap |
| `AVATAR_MAX_CONCURRENT_JOBS` | `1` | How many jobs actually run at once (a semaphore) |
| `AVATAR_MAX_QUEUED_JOBS` | `10` | Total active (queued+running) jobs before `POST /api/tts/avatar` returns 429 |
| `AVATAR_FPS` | `25` | Output video frame rate |
| `AVATAR_MAX_AUDIO_S` | `120.0` | `StubAvatarEngine`'s duration ceiling — see `docs/AVATAR_ARCHITECTURE.md`'s "Long audio" note: this is a "how long a pure-Python frame loop is worth waiting for" limit, not a hardware VRAM limit |
| `AVATAR_JOB_TIMEOUT_S` | `300.0` | Wall-clock cap on one `AvatarEngine.generate()` call |
| `AVATAR_CLEANUP_INTERVAL_S` | `900.0` (15min) | How often the background sweep runs |
| `AVATAR_JOB_RETENTION_S` | `86400.0` (24h) | How long a finished job's files stay downloadable before cleanup removes them |

## Real AI lip sync (optional — real, metered cost)

| Variable | Default | What it controls |
|---|---|---|
| `REPLICATE_API_TOKEN` | unset | When set, activates `ReplicateAvatarEngine` (real AI lip sync via SadTalker on Replicate) instead of the free `StubAvatarEngine` — see `main.py::_select_avatar_engine` and `docs/AVATAR_ARCHITECTURE.md` |

Get a token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
— requires a Replicate account with billing/credit purchased (pay-per-use, no
subscription). **Real cost per generation**, confirmed against actual billed predictions
while building this: ~$0.09–0.15, scaling with audio duration/compute time, not a flat
fee. There is currently no per-user spend cap on top of this app's own concurrency limits
(`avatar_max_concurrent_jobs`/`avatar_max_queued_jobs`) — see
`docs/AVATAR_ARCHITECTURE.md`'s "Open questions" before exposing this on a deployment you
don't fully control access to.

Unset (the default), the app falls back to `StubAvatarEngine` automatically — no error,
no missing feature, just the free procedural placeholder instead of real AI lip sync,
exactly like `OPENAI_API_KEY` being unset only disables the AI dialect rewrite toggle
rather than breaking anything else.

## Running it

Same commands as the rest of this repo — nothing avatar-specific to start separately:

```bash
npm run dev   # backend :8000 (now also serving /api/tts/avatar/*), frontend :5173
```

Open <http://localhost:5173>, click the "الصورة الناطقة" (Talking Avatar) tab next to the
existing "توليد الصوت" tab. Upload a portrait with exactly one clearly visible face, type
Arabic text, pick a dialect/voice/emotion, generate.

## Testing

```bash
.venv/bin/pytest backend/tests -v -m "not integration"    # offline only — 194 pass, 2 skipped,
                                                              # 3 deselected (the real-ffmpeg avatar
                                                              # tests below carry the `integration`
                                                              # marker too, even though they don't
                                                              # need RUN_MODEL_INTEGRATION_TESTS)

.venv/bin/pytest backend/tests                              # everything except the 2 real-model
                                                              # tests (self-skip without the env var
                                                              # below) — 197 pass, 2 skipped; this
                                                              # DOES run the real-ffmpeg avatar tests

RUN_MODEL_INTEGRATION_TESTS=1 .venv/bin/pytest backend/tests/integration -v -m integration
                                                             # everything, including real Lahgtna weights
```

None of the offline tests spend real Replicate credit — `test_replicate_engine.py`
monkeypatches `httpx.AsyncClient` entirely (same "fake the external dependency, test the
logic for real" pattern `test_dialect_rewriter.py` uses for the OpenAI client). The real
integration proof for `ReplicateAvatarEngine` is a live run against the actual API,
documented in this session rather than re-run automatically on every test invocation —
re-run it manually if this code changes in a way that might affect the real request shape
(the exact model version/input field names are pinned and commented in
`replicate_engine.py` for exactly this reason).

Avatar-specific test files, matching this repo's existing `unit`/`contract`/`integration`
split:

- `backend/tests/unit/test_portrait_validator.py`, `test_avatar_engine.py`,
  `test_emotions.py`, `test_tts_cache.py`, `test_avatar_jobs.py`, `test_replicate_engine.py`
  — offline, no ffmpeg, no model weights, no real Replicate calls
  (`FakeAvatarEngine`/`FakeEngine`/a monkeypatched `httpx.AsyncClient` throughout).
- `backend/tests/contract/test_api_avatar.py` — the full HTTP API against fake engines,
  same convention as `test_api_tts.py`.
- `backend/tests/integration/test_stub_engine_real_ffmpeg.py` — the one test that actually
  shells a real `ffmpeg` process and asserts on a real MP4's structure. Marked
  `integration` like the real-model tests, but gates itself on `ffmpeg` being on `PATH`
  (`allow_module_level=True`), not on `RUN_MODEL_INTEGRATION_TESTS` — it needs no model
  weights, so it runs by default under a plain `pytest backend/tests` and only the
  `-m "not integration"` filter skips it.

Frontend: `npm run build`/`npm run lint`/`tsc -b` all pass with the new
`components/avatar-studio/*`, `hooks/useAvatarJob.ts`, `api/avatarClient.ts`,
`types/avatar.ts` — no new frontend dependency was added (plain `fetch` + the browser's
native `EventSource` for SSE, matching this repo's existing "no component framework"
choice, `frontend/DESIGN.md`).

## Extending: swapping the active engine

`backend/app/main.py::_select_avatar_engine()` is the one place engine selection happens —
today it's `ReplicateAvatarEngine` when `REPLICATE_API_TOKEN` is set, `StubAvatarEngine`
otherwise:

```python
def _select_avatar_engine(settings) -> AvatarEngine:
    if settings.replicate_api_token:
        return ReplicateAvatarEngine(settings.replicate_api_token)
    return StubAvatarEngine()
```

A third engine (a different Replicate model, a self-hosted GPU box, the
designed-but-not-implemented `avatar_engines/hf_jobs_engine.py` path) is a change to this
one function — nothing in `api/avatar.py`, `avatar_jobs.py`, or the React UI needs to
change, which is the entire point of the `AvatarEngine` abstraction
(`docs/AVATAR_ARCHITECTURE.md`).
