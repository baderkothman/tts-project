"""The real, GPU-backed `AvatarEngine`: calls SadTalker
(`cjwbw/sadtalker`, https://replicate.com/cjwbw/sadtalker) through
Replicate's REST API. Chosen over self-hosting per
`docs/AVATAR_MODEL_EVALUATION.md` — this app's dev/deploy hardware has no
CUDA, and SadTalker is specifically "audio-driven single image talking
face animation" (the model's own description), the only evaluated
candidate that actually takes a single portrait photo rather than an
existing driving video. Verified for real against the live API while
building this (a real prediction, a real downloaded MP4, real visible
mouth/head movement across frames) — not wired in blind.

Real, metered cost per call (~$0.09-0.15/generation observed; scales with
audio duration/compute time, not a flat fee — see
docs/AVATAR_SETUP.md). This is why `main.py` only activates this engine
when `REPLICATE_API_TOKEN` is explicitly set (`Settings.replicate_api_token`)
— unset, the app falls back to the free `StubAvatarEngine`, the same
"optional credential, honest fallback" shape `dialect_rewriter.py` already
uses for `OPENAI_API_KEY`.

## Emotion mapping

SadTalker's own controls are `expression_scale` (float, model's default
1.0 — "a larger value will make the expression motion stronger") and
`still_mode` (bool — "fewer head motion"). Neither is a rich vocabulary,
so the mapping from this app's `EmotionConfig` is necessarily coarse:

- `expression_scale = 1.0 + emotion.expression_strength` — since
  `expression_strength` is 0..0.6 across every preset (see
  `data/emotions.py`), this stays in SadTalker's own sane range (1.0-1.6)
  rather than pushing toward known-distorted extremes.
- `still_mode = emotion.head_motion < 0.15` — SadTalker's own field
  description ties `still_mode` directly to head-motion amount, so the
  calmer presets (neutral/calm/professional, all <0.15 head_motion) get
  `still_mode=True` and the more energetic ones (happy/excited/sad) get
  real head movement.
- `use_eyeblink = True`, always — a real capability `StubAvatarEngine`
  explicitly cannot offer (no eye landmarks available there); this is the
  concrete case that gap was written for.
- `pose_style` is left at the model's own default (0) — its docs give no
  semantic meaning to other values beyond "pose style", so there's nothing
  honest to map `EmotionConfig` onto here.

## Cancellation (see avatar_jobs.py's module docstring)

Unlike `StubAvatarEngine`'s local subprocess, a Replicate prediction *can*
be cancelled mid-flight for real (`POST .../predictions/{id}/cancel`,
tested manually against the live API while building this). Not wired in
yet: `AvatarEngine.generate()`'s signature carries no cancellation token
(a deliberate, documented scope boundary — see `avatar_engine.py`'s
docstring), so there is nothing for this engine to receive a cancellation
signal through. Threading a token through the ABC is the natural next
step now that a concrete use for it exists.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
import soundfile as sf

from backend.app.services.avatar_engine import AvatarEngine, AvatarEngineError, AvatarOptions, AvatarResult, EmotionConfig

logger = logging.getLogger("lahgtna.avatar.replicate_engine")

_API_BASE = "https://api.replicate.com/v1"
# Pinned to a specific version, not "latest" — verified directly against
# this exact version's real input schema (source_image/driven_audio
# required; still_mode/use_eyeblink/expression_scale/pose_style/preprocess/
# facerender/size_of_image/use_enhancer optional) while building this. An
# unpinned "latest" could silently change the input contract underneath
# this code.
_MODEL_VERSION = "a519cc0cfebaaeade068b23899165a11ec76aaa1d2b313d40d214f204ec957a3"

_POLL_INTERVAL_S = 3.0
_MAX_POLLS = 200  # ~10min hard ceiling, belt-and-suspenders under the job manager's own avatar_job_timeout_s
_OUTPUT_SIZE_PX = 256  # SadTalker's own default `size_of_image` — matches what's actually requested below


class ReplicateAvatarEngine(AvatarEngine):
    name = "replicate:sadtalker"

    def __init__(self, api_token: str) -> None:
        self._token = api_token

    async def generate(
        self, *, image_path: Path, audio_path: Path, emotion: EmotionConfig, options: AvatarOptions
    ) -> AvatarResult:
        if not options.work_dir:
            raise AvatarEngineError("generation_failed", "No work directory provided for video output")

        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
            image_url = await self._upload(client, image_path)
            audio_url = await self._upload(client, audio_path)
            prediction_id = await self._create_prediction(client, image_url, audio_url, emotion)
            output_url = await self._poll_until_done(client, prediction_id)
            video_bytes = await self._download(client, output_url)

        video_path = options.work_dir / "output.mp4"
        video_path.write_bytes(video_bytes)

        info = sf.info(str(audio_path))
        duration_s = info.frames / info.samplerate if info.samplerate else 0.0

        return AvatarResult(
            video_path=video_path,
            width=_OUTPUT_SIZE_PX,
            height=_OUTPUT_SIZE_PX,
            duration_s=duration_s,
            engine_notes=["motion: real AI lip sync (SadTalker via Replicate) — includes real eye blinking"],
        )

    async def _upload(self, client: httpx.AsyncClient, path: Path) -> str:
        try:
            with path.open("rb") as f:
                response = await client.post(f"{_API_BASE}/files", files={"content": (path.name, f)})
        except httpx.HTTPError as exc:
            raise AvatarEngineError("not_available", "Could not reach Replicate to upload input") from exc
        if response.status_code >= 400:
            self._raise_for_status(response, context="uploading a file")
        return response.json()["urls"]["get"]

    async def _create_prediction(
        self, client: httpx.AsyncClient, image_url: str, audio_url: str, emotion: EmotionConfig
    ) -> str:
        payload = {
            "version": _MODEL_VERSION,
            "input": {
                "source_image": image_url,
                "driven_audio": audio_url,
                "still_mode": emotion.head_motion < 0.15,
                "use_eyeblink": True,
                "expression_scale": round(1.0 + emotion.expression_strength, 2),
                "size_of_image": _OUTPUT_SIZE_PX,
            },
        }
        try:
            response = await client.post(f"{_API_BASE}/predictions", json=payload)
        except httpx.HTTPError as exc:
            raise AvatarEngineError("not_available", "Could not reach Replicate to start generation") from exc
        if response.status_code >= 400:
            self._raise_for_status(response, context="starting generation")
        return response.json()["id"]

    async def _poll_until_done(self, client: httpx.AsyncClient, prediction_id: str) -> str:
        for _ in range(_MAX_POLLS):
            try:
                response = await client.get(f"{_API_BASE}/predictions/{prediction_id}")
            except httpx.HTTPError as exc:
                raise AvatarEngineError("not_available", "Lost connection to Replicate while generating") from exc
            if response.status_code >= 400:
                self._raise_for_status(response, context="checking generation status")

            body = response.json()
            status = body["status"]
            if status == "succeeded":
                output = body.get("output")
                if not output:
                    raise AvatarEngineError("generation_failed", "Replicate reported success but returned no video")
                return output
            if status in ("failed", "canceled"):
                logger.warning("Replicate prediction %s %s: %s", prediction_id, status, body.get("error"))
                raise AvatarEngineError("generation_failed", "The AI video generation service could not process this request")
            await asyncio.sleep(_POLL_INTERVAL_S)

        raise AvatarEngineError("generation_failed", "Timed out waiting for Replicate")

    async def _download(self, client: httpx.AsyncClient, url: str) -> bytes:
        try:
            response = await client.get(url)
        except httpx.HTTPError as exc:
            raise AvatarEngineError("not_available", "Could not download the generated video") from exc
        if response.status_code >= 400:
            self._raise_for_status(response, context="downloading the generated video")
        return response.content

    def _raise_for_status(self, response: httpx.Response, *, context: str) -> None:
        if response.status_code == 401:
            raise AvatarEngineError("not_available", "Replicate rejected this server's API token")
        if response.status_code == 402:
            raise AvatarEngineError("not_available", "This server's Replicate account has insufficient credit")
        if response.status_code == 429:
            raise AvatarEngineError("generation_failed", "Replicate is rate-limiting this server — try again shortly")
        logger.warning("Replicate error while %s: %s %s", context, response.status_code, response.text[:500])
        raise AvatarEngineError("generation_failed", f"Replicate request failed while {context}")
