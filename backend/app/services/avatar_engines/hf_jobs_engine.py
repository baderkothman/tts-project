"""The designed-but-not-yet-implemented real engine: runs an actual
audio-driven talking-head model (per `docs/AVATAR_MODEL_EVALUATION.md`'s
recommendation — MuseTalk first) as a remote **Hugging Face Job**, since
this app's local dev hardware has no CUDA (Apple Silicon/MPS only — see
that doc's hardware section) and this repo already has `HF_TOKEN`
configured and already depends on the Hugging Face Hub for its TTS model
weights, so no new cloud account/credential is needed to get real GPU time.

Deliberately not implemented in this pass: dispatching a real HF Job spends
real GPU-minutes (i.e. money) on every call, and doing that from inside an
agent session without a human explicitly triggering each run would violate
this project's own AGENTS.md ("Require fresh human confirmation immediately
before... financial... actions"). This class exists so the `AvatarEngine`
abstraction has a concrete second implementation to design against — not a
mock, a real plan — and so wiring it in later is a configuration change
(`avatar_jobs.py`'s engine selection), not an architecture change.

## The actual plan, when this is picked up

1. Package a small inference script (`generate.py`: loads MuseTalk once,
   accepts `--image`, `--audio`, `--out`) and a `requirements.txt` pinning
   MuseTalk's real CUDA-only dependencies — none of which need to install
   in *this* app's own environment, only in the Job's container.
2. `hf jobs run` (per the `hf-cli` skill) that script on a GPU-flavor
   (`--flavor a10g-small` or similar — see MuseTalk's own documented VRAM
   floor in the evaluation doc before picking a flavor), passing the
   portrait/audio as job inputs (uploaded to a scratch HF dataset repo or
   passed as a signed URL — whichever `hf jobs` supports most simply) and
   downloading the resulting MP4 when the job completes.
3. `generate()` below becomes: upload inputs -> `hf jobs run` -> poll job
   status -> download output -> return `AvatarResult`. Every step already
   has a natural `AvatarJobStatus` mapping in `avatar_jobs.py`
   (`preparing_avatar` while uploading/dispatching, `generating_video`
   while the remote job runs, `encoding` is folded into the remote job
   itself here since MuseTalk's own pipeline already outputs MP4).
4. Cost/quota control: this needs a real per-user or global job budget
   before it's safe to expose publicly — see `docs/AVATAR_ARCHITECTURE.md`'s
   "Open questions" section. Not designed in detail here because it depends
   on a business decision (who pays, what the cap is) this codebase can't
   make on its own.

`generate()` raises `AvatarEngineError("not_available", ...)` unconditionally
until the above is actually built and a real HF Jobs configuration
(endpoint/flavor/budget) is supplied — this is not a placeholder that
silently no-ops or fakes a result; a caller that reaches this engine gets a
clear, typed failure, exactly like `dialect_rewriter.is_configured()`
reporting an unset `OPENAI_API_KEY` honestly rather than pretending the
feature works.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.services.avatar_engine import AvatarEngine, AvatarEngineError, AvatarOptions, AvatarResult, EmotionConfig


class HFJobsAvatarEngine(AvatarEngine):
    name = "hf-jobs:musetalk"

    async def generate(
        self,
        *,
        image_path: Path,
        audio_path: Path,
        emotion: EmotionConfig,
        options: AvatarOptions,
    ) -> AvatarResult:
        raise AvatarEngineError(
            "not_available",
            "The real GPU-backed avatar engine (HF Jobs / MuseTalk) is designed but not yet "
            "implemented — see avatar_engines/hf_jobs_engine.py's module docstring for the plan. "
            "Only the stub-procedural engine is available right now.",
        )
