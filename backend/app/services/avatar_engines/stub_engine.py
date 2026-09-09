"""The default `AvatarEngine` while no real GPU inference is wired up (see
`docs/AVATAR_MODEL_EVALUATION.md` for why: every genuinely audio-driven
candidate model is CUDA-only in practice, and this app's local dev hardware
has no CUDA — Apple Silicon/MPS only). This is a deliberately honest
placeholder, not a disguised imitation of AI lip sync:

- **Real, not mocked, output.** Every call actually shells out to `ffmpeg`
  and produces a genuine H.264/yuv420p MP4 with the real generated audio
  muxed in — nothing here is a canned/fixture file.
- **Real, audio-reactive motion**, so the face is never literally a static
  frame (the brief's own explicit requirement): a subtle Ken-Burns
  zoom/pan (amplitude scaled by `EmotionConfig.head_motion`) for idle
  motion, plus a mouth-region vertical pulse driven by the *actual* audio's
  RMS envelope (amplitude scaled by `EmotionConfig.expression_strength`) —
  a real signal, not a random wiggle, but explicitly **not** phoneme-
  accurate lip sync. Same honesty pattern as the avatar identity feature's
  `talking` state (`frontend/src/components/avatar/BayanAvatar.tsx`): an
  audio-reactive approximation, clearly labeled as one.
- **What it deliberately does not attempt**: blinking and eye motion.
  Both would need real eye-landmark coordinates to place convincingly on an
  arbitrary uploaded photo; this engine only has a face bounding box
  (`portrait_validator.py`'s detector), and a pixel effect drawn in
  approximately the right place would read as a visible artifact, not a
  blink. `EmotionConfig.blink_rate`/`eye_motion` are accepted (part of the
  shared interface) but intentionally unused here — see `AvatarEngine`'s
  own docstring for why a partial, honest mapping is the documented,
  expected shape for an engine that can't represent every field. `smile`
  (a geometric mouth-corner warp) is the same story: not attempted without
  landmarks.

Replacing this with a real engine (`avatar_engines/hf_jobs_engine.py`) is
exactly the swap `AvatarEngine` exists to make cheap — see
`avatar_jobs.py`'s engine selection.
"""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image

from backend.app.services.avatar_engine import AvatarEngine, AvatarEngineError, AvatarOptions, AvatarResult, EmotionConfig

logger = logging.getLogger("lahgtna.avatar.stub_engine")

_MIN_AUDIO_S = 0.05
# How much of the frame the mouth-pulse crop covers, as a fraction of the
# detected face box — a fixed heuristic (no landmarks available), tuned by
# eye against a handful of real portraits during development, not derived
# from any dataset.
_MOUTH_X0, _MOUTH_X1 = 0.28, 0.72
_MOUTH_Y0, _MOUTH_Y1 = 0.62, 0.94


class StubAvatarEngine(AvatarEngine):
    name = "stub-procedural"

    async def generate(
        self,
        *,
        image_path: Path,
        audio_path: Path,
        emotion: EmotionConfig,
        options: AvatarOptions,
    ) -> AvatarResult:
        import asyncio

        return await asyncio.to_thread(self._generate_sync, image_path, audio_path, emotion, options)

    def _generate_sync(
        self,
        image_path: Path,
        audio_path: Path,
        emotion: EmotionConfig,
        options: AvatarOptions,
    ) -> AvatarResult:
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            raise AvatarEngineError("not_available", "ffmpeg is not installed on this server")

        samples, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=False)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        duration_s = len(samples) / sample_rate if sample_rate else 0.0
        if duration_s < _MIN_AUDIO_S:
            raise AvatarEngineError("generation_failed", "Generated audio was empty or silent")
        if duration_s > options.max_duration_s:
            raise AvatarEngineError(
                "invalid_input",
                f"Audio duration {duration_s:.1f}s exceeds this engine's {options.max_duration_s:.0f}s limit "
                "— see docs/AVATAR_ARCHITECTURE.md's 'Long audio' section",
            )

        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        # yuv420p requires even dimensions.
        width -= width % 2
        height -= height % 2
        if (image.width, image.height) != (width, height):
            image = image.crop((0, 0, width, height))

        fps = options.fps
        n_frames = max(1, round(duration_s * fps))
        rms_envelope = _frame_rms_envelope(samples, sample_rate, fps=fps, n_frames=n_frames)

        mouth_box = _mouth_box(options.face_box, width, height)
        engine_notes = [
            "motion: procedural Ken-Burns idle pan/zoom + audio-RMS mouth-region pulse "
            "(no AI lip sync, no blink/eye motion — see StubAvatarEngine's module docstring)"
        ]
        if mouth_box is None:
            engine_notes.append("no face_box supplied — mouth pulse skipped, idle motion only")

        if not options.work_dir:
            raise AvatarEngineError("generation_failed", "No work directory provided for video output")
        output_path = options.work_dir / "output.mp4"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        try:
            # stdout is DEVNULL, not PIPE: the encoded video goes straight to
            # `output_path`, ffmpeg writes nothing of interest to stdout, and
            # leaving it unpiped avoids a second OS pipe buffer to drain.
            # stderr stays piped (for diagnostics on failure) but is only
            # ever read *after* the process has exited (see below) — never
            # concurrently with the stdin writes below, which was the
            # source of a real bug here: calling `Popen.communicate()` after
            # already manually closing `proc.stdin` raises `ValueError:
            # flush of closed file` (communicate() tries to manage stdin
            # itself). `wait()` + a direct `stderr.read()` avoids that.
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except OSError as exc:
            raise AvatarEngineError("not_available", "Could not start ffmpeg") from exc

        assert proc.stdin is not None
        try:
            for i in range(n_frames):
                frame = _render_frame(
                    image, width=width, height=height, t=i / fps, emotion=emotion,
                    mouth_box=mouth_box, rms=rms_envelope[i] if i < len(rms_envelope) else 0.0,
                )
                proc.stdin.write(np.asarray(frame).tobytes())
        except BrokenPipeError:
            pass  # ffmpeg exited early — the returncode check below reports it
        finally:
            proc.stdin.close()

        try:
            proc.wait(timeout=max(30.0, duration_s * 4))
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise AvatarEngineError("generation_failed", "Video encoding timed out")

        if proc.returncode != 0 or not output_path.exists():
            stderr = proc.stderr.read() if proc.stderr else b""
            logger.warning("ffmpeg failed (code %s): %s", proc.returncode, stderr.decode("utf-8", "replace")[-2000:])
            raise AvatarEngineError("generation_failed", "Video encoding failed")

        return AvatarResult(video_path=output_path, width=width, height=height, duration_s=duration_s, engine_notes=engine_notes)


def _frame_rms_envelope(samples: np.ndarray, sample_rate: int, *, fps: int, n_frames: int) -> list[float]:
    """One RMS value per output video frame, normalized to ~0..1 against
    this clip's own 95th-percentile loudness (robust to a single loud
    outlier sample) rather than its absolute max."""
    frame_len = max(1, round(sample_rate / fps))
    raw = []
    for i in range(n_frames):
        window = samples[i * frame_len : (i + 1) * frame_len]
        raw.append(float(np.sqrt(np.mean(window**2))) if len(window) else 0.0)
    peak = float(np.percentile(raw, 95)) if raw else 0.0
    if peak < 1e-6:
        return [0.0] * n_frames
    return [min(1.0, v / peak) for v in raw]


def _mouth_box(
    face_box: tuple[int, int, int, int] | None, width: int, height: int
) -> tuple[int, int, int, int] | None:
    if face_box is None:
        return None
    fx, fy, fw, fh = face_box
    x0 = fx + int(fw * _MOUTH_X0)
    x1 = fx + int(fw * _MOUTH_X1)
    y0 = fy + int(fh * _MOUTH_Y0)
    y1 = fy + int(fh * _MOUTH_Y1)
    return (max(0, x0), max(0, y0), min(width, x1), min(height, y1))


def _render_frame(
    base: Image.Image,
    *,
    width: int,
    height: int,
    t: float,
    emotion: EmotionConfig,
    mouth_box: tuple[int, int, int, int] | None,
    rms: float,
) -> Image.Image:
    frame = _ken_burns(base, width=width, height=height, t=t, head_motion=emotion.head_motion)
    if mouth_box is not None:
        frame = _pulse_mouth(frame, mouth_box, strength=emotion.expression_strength, rms=rms)
    return frame


def _ken_burns(image: Image.Image, *, width: int, height: int, t: float, head_motion: float) -> Image.Image:
    """Subtle idle zoom + pan so the portrait is never a literally static
    frame, even during silence. Two independent, non-matching sinusoid
    periods (4s zoom, 6s pan) so the loop doesn't read as a metronomic
    back-and-forth over a longer clip."""
    zoom_amplitude = 0.015 + 0.02 * head_motion
    zoom = 1.0 + zoom_amplitude * math.sin(2 * math.pi * t / 4.0)
    pan_amplitude = 0.01 * head_motion
    pan_x = pan_amplitude * width * math.sin(2 * math.pi * t / 6.0 + 1.0)
    pan_y = pan_amplitude * height * math.sin(2 * math.pi * t / 5.0)

    crop_w = width / zoom
    crop_h = height / zoom
    cx = width / 2 + pan_x
    cy = height / 2 + pan_y
    left = max(0.0, min(width - crop_w, cx - crop_w / 2))
    top = max(0.0, min(height - crop_h, cy - crop_h / 2))
    cropped = image.crop((int(left), int(top), int(left + crop_w), int(top + crop_h)))
    return cropped.resize((width, height), Image.LANCZOS)


def _pulse_mouth(frame: Image.Image, box: tuple[int, int, int, int], *, strength: float, rms: float) -> Image.Image:
    """Vertically scales the mouth-region crop around its own center,
    proportional to the real audio RMS at this frame — a crude but honest
    "not literally frozen while talking" cue, not phoneme lip sync. Clamped
    well short of a cartoonish gape."""
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return frame
    scale = 1.0 + min(0.5, (0.15 + 0.25 * strength) * rms)
    if scale <= 1.001:
        return frame

    mouth = frame.crop(box)
    new_h = max(1, int(mouth.height * scale))
    stretched = mouth.resize((mouth.width, new_h), Image.LANCZOS)

    cy = (y0 + y1) // 2
    paste_y = cy - new_h // 2
    out = frame.copy()
    out.paste(stretched, (x0, paste_y))
    return out
