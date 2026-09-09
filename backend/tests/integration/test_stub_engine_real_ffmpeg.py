"""The one test in this suite that actually shells out to a real `ffmpeg`
binary — everything else avatar-related (`test_avatar_jobs.py`,
`test_api_avatar.py`) uses `FakeAvatarEngine` instead. Marked `integration`
like `test_live_model.py`'s real-model tests, for the same reason: this
needs a real environment resource (`ffmpeg` on PATH) that isn't guaranteed
everywhere this suite runs, so it skips cleanly rather than failing when
absent."""

from __future__ import annotations

import shutil

import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from backend.app.services.avatar_engine import AvatarOptions, EmotionConfig
from backend.app.services.avatar_engines.stub_engine import StubAvatarEngine

pytestmark = pytest.mark.integration

if not shutil.which("ffmpeg"):
    pytest.skip("ffmpeg is not installed", allow_module_level=True)


def _write_sine_wav(path, *, duration_s: float = 1.0, sample_rate: int = 16000) -> None:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    # Amplitude envelope that actually varies (silence -> loud -> silence)
    # so the mouth-pulse code path has real signal to react to, not a flat
    # tone that would exercise the same branch every frame.
    envelope = np.sin(np.pi * t / duration_s) ** 2
    samples = (0.3 * envelope * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    sf.write(str(path), samples, sample_rate)


def _write_portrait(path, *, size=(320, 320)) -> None:
    Image.new("RGB", size, (180, 140, 110)).save(path, format="PNG")


async def test_stub_engine_produces_a_real_valid_mp4(tmp_path):
    audio_path = tmp_path / "audio.wav"
    image_path = tmp_path / "portrait.png"
    _write_sine_wav(audio_path, duration_s=1.0)
    _write_portrait(image_path)

    engine = StubAvatarEngine()
    options = AvatarOptions(fps=15, work_dir=tmp_path, face_box=(60, 50, 200, 200))
    result = await engine.generate(
        image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("happy"), options=options
    )

    assert result.video_path.exists()
    assert result.video_path.stat().st_size > 1000
    assert result.width % 2 == 0 and result.height % 2 == 0
    assert 0.8 < result.duration_s <= 1.0
    assert any("no AI lip sync" in note for note in result.engine_notes)

    # A real MP4 has a real container header — cheap structural check
    # without needing ffprobe as a second test dependency.
    header = result.video_path.read_bytes()[:12]
    assert b"ftyp" in header


async def test_stub_engine_rejects_audio_past_its_duration_limit(tmp_path):
    audio_path = tmp_path / "audio.wav"
    image_path = tmp_path / "portrait.png"
    _write_sine_wav(audio_path, duration_s=1.0)
    _write_portrait(image_path)

    engine = StubAvatarEngine()
    options = AvatarOptions(fps=15, max_duration_s=0.5, work_dir=tmp_path, face_box=None)

    from backend.app.services.avatar_engine import AvatarEngineError

    with pytest.raises(AvatarEngineError) as exc_info:
        await engine.generate(
            image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("neutral"), options=options
        )
    assert exc_info.value.kind == "invalid_input"


async def test_stub_engine_works_without_a_face_box(tmp_path):
    # No portrait_validator involved at all here — the engine must still
    # produce a real video with idle motion only (no mouth pulse) when
    # face_box is None.
    audio_path = tmp_path / "audio.wav"
    image_path = tmp_path / "portrait.png"
    _write_sine_wav(audio_path, duration_s=0.5)
    _write_portrait(image_path)

    engine = StubAvatarEngine()
    options = AvatarOptions(fps=10, work_dir=tmp_path, face_box=None)
    result = await engine.generate(
        image_path=image_path, audio_path=audio_path, emotion=EmotionConfig.for_emotion("calm"), options=options
    )
    assert result.video_path.exists()
    assert any("mouth pulse skipped" in note for note in result.engine_notes)
