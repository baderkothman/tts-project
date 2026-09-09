"""Deterministic test double for `AvatarEngine` — offline, no ffmpeg, no
model. Mirrors `services/fake_engine.py`'s own pattern for `TTSEngine`:
same public surface, real (if trivial) output, used by `avatar_jobs.py`'s
and `api/avatar.py`'s test suites so neither depends on a real subprocess
or GPU. Not used by `backend/app/main.py`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.services.avatar_engine import (
    AvatarEngine,
    AvatarEngineError,
    AvatarEngineErrorKind,
    AvatarOptions,
    AvatarResult,
    EmotionConfig,
)


class FakeAvatarEngine(AvatarEngine):
    name = "fake"

    def __init__(self, *, fail: AvatarEngineErrorKind | None = None, delay_s: float = 0.0) -> None:
        self._fail = fail
        self._delay_s = delay_s
        self.calls: list[tuple[Path, Path, EmotionConfig, AvatarOptions]] = []

    async def generate(
        self, *, image_path: Path, audio_path: Path, emotion: EmotionConfig, options: AvatarOptions
    ) -> AvatarResult:
        self.calls.append((image_path, audio_path, emotion, options))
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        if self._fail is not None:
            raise AvatarEngineError(self._fail, f"induced {self._fail} failure")

        assert options.work_dir is not None
        video_path = options.work_dir / "output.mp4"
        video_path.write_bytes(b"FAKE-MP4-CONTENT")
        return AvatarResult(video_path=video_path, width=64, height=64, duration_s=1.0, engine_notes=["fake engine — no real encoding"])
