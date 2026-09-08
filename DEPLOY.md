# Deploying to Railway

**Live**: <https://lahgtna-tts-production.up.railway.app> — deployed and
verified end-to-end (real audio generated through the public URL, not just a
health check) as of 2026-09-08. Project: `lahgtna-tts` in Bader Othman's
Railway workspace.

Single-service deployment: one container runs FastAPI, which serves both the
API and the built frontend from one origin (`backend/app/main.py` already
mounts `frontend/dist/` when present — see `README.md`'s "Run" section for
the same single-process mode used locally). `Dockerfile` and `railway.json`
at the repo root define the build; Railway auto-detects both.

## Honest state of the live deployment

- **Works.** `POST /api/tts` returns real generated audio through the public
  URL — verified directly, not assumed.
- **CPU-only, and slow.** Real measured number from the live deployment: one
  MSA sentence (`"مرحبا بكم في هذا الاختبار المباشر على الإنترنت"`, ~4s of
  audio) took **107 seconds** to generate — **RTF ≈ 27**, vs. RTF 0.6–1.0 on
  local MPS (`docs/PERFORMANCE_BENCHMARKS.md`). This is a standard Railway
  service with no GPU; §"What this doesn't solve" below is not hypothetical
  here, it's what's actually running.
- **Diacritization is currently degraded, not broken.** The Volume (5GB,
  Railway's CLI-default size — see "A volume-size bug" below) fits Lahgtna's
  ~2.4GB but not the Fine-Tashkeel diacritizer's ~1.2GB on top of it plus
  working overhead, so the diacritizer fails to load. This used to crash
  every `/api/tts` request with a 500 (see "A real bug" below, now fixed) —
  it now degrades exactly the way `main.py`'s startup already promised:
  Arabic is spoken undiacritized rather than the request failing. Each
  response segment's `diacritized` field honestly reflects this
  (`false` when it couldn't run). Fix is a bigger volume — see below.

## Why this needs a bit more than "connect repo and go"

This isn't a stateless web app — `backend/app/services/inference.py` loads
~3.6GB of model weights (Lahgtna + the Fine-Tashkeel diacritizer) into
memory once at startup and keeps them warm. Two consequences that don't
apply to a typical Railway deploy:

1. **A persistent Volume for the model cache.** Without one, every
   redeploy/restart re-downloads ~3.6GB from Hugging Face Hub before the
   app is usable again — slow, and needlessly hits HF's rate limits. With
   one, only the *first* boot pays that cost.
2. **No GPU/MPS on a standard Railway service.** `device: "auto"`
   (`backend/app/config.py`) already falls back to CPU automatically — no
   code change needed — but CPU inference is meaningfully slower than the
   MPS numbers in `docs/PERFORMANCE_BENCHMARKS.md`. This is an honest
   architectural limit of this host, not a bug: re-measure latency on
   whatever Railway plan/instance size you actually deploy to before
   treating any local number as representative.

## One-time setup

1. **Create the Railway project** from this repo (Railway dashboard → New
   Project → Deploy from GitHub repo, or `railway init` with the CLI). It
   will detect `railway.json` and build via `Dockerfile` automatically.

2. **Add a Volume** (Railway dashboard → your service → Volumes → New
   Volume):
   - Mount path: `/data/hf_cache`
   - This matches `Dockerfile`'s `ENV HF_HOME=/data/hf_cache` — the model
     loaders read `$HF_HOME` at runtime (`config.py`'s `resolved_hf_home`),
     so nothing else needs to change for the volume to actually get used.
   - **Size it to at least 8-10GB, not the 5GB CLI default.** Lahgtna
     (~2.4GB) + Fine-Tashkeel (~1.2GB) + Kokoro + working overhead doesn't
     comfortably fit in 5GB — confirmed directly on the live deployment (see
     "A volume-size bug" below). The CLI's `railway volume add` has no
     `--size` flag and the GraphQL API's `VolumeInstanceUpdateInput` has no
     size field either (checked via `railway api search`) — resizing an
     existing volume appears to be dashboard-only (or plan-tier-gated);
     size it generously the first time rather than fighting a resize later.

3. **Set environment variables** (Railway dashboard → your service →
   Variables). None are required — the model downloads anonymously — but
   these are worth setting:
   - `HF_TOKEN` — optional; raises Hugging Face Hub's anonymous download
     rate limit for the first boot's ~3.6GB pull. Not needed for TTS
     synthesis itself.
   - `OPENAI_API_KEY` — optional; only enables the opt-in "AI dialect
     rewrite" toggle (`services/dialect_rewriter.py`, see README). Leave it
     unset and that toggle is reported unavailable; everything else on this
     deploy works identically without it.
   - `HF_HUB_DISABLE_XET=1` — see "A disk-space bug" below. Xet-based
     downloads need roughly 2x a file's size in transient staging space
     during "reconstruction"; on a tightly-sized volume that's the
     difference between fitting and an `ENOSPC` crash mid-download. Cheap
     to set regardless of volume size.
   - Do **not** set `PORT` yourself — Railway injects it. But **do** make
     sure whatever you pass to `railway domain --port` (or the dashboard's
     domain target port) matches Railway's *actual* injected value — see
     "A port-mismatch bug" below; it is not reliably 8000.

4. **Deploy.** First boot will take a while (image pull + ~3.6GB model
   download into the new volume) — `GET /api/health` responds within
   seconds regardless (it reports `"status": "loading"` while the model
   loads in a background task, per `main.py`'s lifespan — this is the same
   behavior local dev already has), so Railway's healthcheck
   (`railway.json`'s `healthcheckPath`) passes quickly even though
   `/api/tts` itself still 503s until loading finishes. Watch the deploy
   logs for `Model loaded in Ns` (from `inference.py`) to know when it's
   actually ready to generate.

## Redeploys

With the volume in place, a normal `git push` → Railway rebuild only
re-runs what changed (Docker layer caching for unchanged deps/frontend
files) and reuses the already-downloaded model weights from the volume —
no repeat of the first-boot download cost.

## Local smoke test before pushing

```bash
docker build --platform linux/amd64 -t lahgtna-tts:test .
docker run --rm --platform linux/amd64 -p 8000:8000 -e PORT=8000 lahgtna-tts:test
# in another terminal:
curl http://localhost:8000/api/health   # should respond almost immediately
```

`--platform linux/amd64` matters if you're building on Apple Silicon —
Railway's infrastructure is x86_64, and Docker otherwise builds for your
host's architecture by default.

This downloads the model into the *container's* ephemeral filesystem (no
volume locally) — fine for a smoke test, but don't expect it to persist
across `docker run`s the way the Railway volume persists across deploys.

**Verified directly** (not just assumed to work): built and ran this exact
image — `/api/health` responds within ~15s with `{"status":"loading",...}`,
`/` serves the built frontend (HTTP 200, confirming the single-process
static-mount mode), and the container logs show `device=cpu` selected
automatically (no GPU/MPS in the container — correct fallback, no code
change needed) with real Hugging Face downloads starting. Final image:
**688MB**.

**A real bug this caught, not a hypothetical one**: the first build attempt
spent 25+ minutes downloading a 454MB CUDA-enabled `torch` wheel, then a
651MB `nvidia_cudnn` wheel, with more NVIDIA packages still queued —
`pip install .` on Linux resolves plain PyPI `torch`, which defaults to the
CUDA build, dragging in gigabytes of libraries a GPU-less Railway service
will never use. Fixed by installing the CPU wheel from PyTorch's own index
*before* the main install (`Dockerfile`) — confirmed after the fix:
`torch 2.14.0+cpu`, `torch.cuda.is_available()` → `False`, no `nvidia_*`
packages anywhere in the install log.

## Three more real bugs found deploying this for real

Caught by actually deploying and hitting the live URL, not by inspection —
recorded here so the next redeploy doesn't rediscover them the hard way.

**A port-mismatch bug.** `railway domain --port 8000` was set assuming
Railway's injected `$PORT` would be 8000 (matching the Dockerfile's
`EXPOSE`) — it wasn't. Deploy logs showed `Uvicorn running on
http://0.0.0.0:8080`; the domain was still routing to 8000, giving a clean
502 ("Application failed to respond") even though the app was healthy.
Fixed with `railway domain update <id> --port 8080` to match reality. Don't
assume a specific `$PORT` value — read it from the deploy logs (or the
service's Variables tab) before wiring a domain to it.

**A volume-size bug.** The Volume created via `railway volume add` (no
`--size` flag exists) came out at Railway's 5GB default. Lahgtna alone
(~2.4GB) fit and loaded fine (`model_loaded: true`), but the diacritizer's
~1.2GB on top of it didn't — `OSError: [Errno 28] No space left on device`
mid-download, confirmed in deploy logs. 5GB is too tight for this app's
full model set; see step 2 above.

**A disk-space-adjacent bug in `hf-xet`.** Before finding the volume-size
issue, the *first* symptom was `/api/health` returning
`"detail": "Task error: File reconstruction error: IO Error: No space left
on device"` during Lahgtna's own download — worse than the plain diacritizer
failure above. Root cause: `huggingface_hub`'s newer Xet transfer backend
downloads content-addressed chunks and *reconstructs* the final file from
them, needing roughly double the file's size in transient space during that
reconstruction step. Setting `HF_HUB_DISABLE_XET=1`
([huggingface_hub docs](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables))
falls back to plain HTTP streaming straight to the target file — no
double-staging — and Lahgtna then loaded successfully on the same 5GB
volume. Set it regardless of volume size; it's a pure win with no downside
found.

**A real, still-live bug this fixed in application code, not just infra**:
the diacritizer's disk-space failure above didn't just fail once at
startup — `main.py`'s lifespan already promises a failed diacritizer
"degrades gracefully (diacritization is skipped)" rather than blocking the
app, but that promise only held at *startup*. Every subsequent `/api/tts`
request lazily retried the same doomed download (`diacritizer.diacritize()`
→ `_run_model()` → `_load()`), and an unhandled exception there propagated
into a 500 for the whole request instead of degrading. Fixed in
`backend/app/services/diacritizer.py`: `_load()` now records `_load_error`
and fails fast on retry instead of re-attempting an already-failed
multi-hundred-MB download on every request, and the call site catches a
failure and returns the text undiacritized — honoring the startup promise
at request time too. 3 new regression tests in `test_diacritizer.py`.

## What this doesn't solve

- **Scaling / concurrency**: still one process, one model instance, one
  request at a time (`TTSEngine`'s `asyncio.Lock` — see
  `docs/PRODUCTION_ARCHITECTURE.md` §6 for the real horizontal-scaling
  recommendation, which this single-service Railway setup does not
  implement).
- **GPU inference**: not available on a standard Railway service, and this
  is not a hypothetical caveat — the live deployment measured RTF ≈ 27 (see
  above), ~27x slower than local MPS. If that's unacceptable, that's a real
  constraint to weigh against a GPU-capable host (Modal, RunPod, Fly.io GPU,
  etc.) — see `docs/PRODUCTION_ARCHITECTURE.md`.
- **Diacritization**, until the volume is resized to fit it (see "A
  volume-size bug" above) — Arabic currently ships undiacritized on this
  deployment specifically, not as a general limitation of the app.
