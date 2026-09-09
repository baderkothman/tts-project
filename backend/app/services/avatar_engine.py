"""The `AvatarEngine` abstraction: the one seam the Talking Avatar feature
depends on, everywhere else in the app.

This mirrors `services/inference.py`'s relationship to `TTSEngine` — the
rest of the app (job manager, API layer) is written against this interface,
never against a specific model. Swapping the engine that actually produces
the MP4 (e.g. from `StubAvatarEngine` to a real GPU-backed one — see
`avatar_engines/hf_jobs_engine.py`) means changing which class
`avatar_jobs.py` instantiates, not the job manager, the API, or the React
UI. See `docs/AVATAR_ARCHITECTURE.md` for the full rationale.

Kept in its own module (not `avatar_engines/`) because `EmotionConfig` and
`AvatarOptions` are shared vocabulary every engine and the job manager both
need to import — putting them inside one specific engine's module would
make every other engine depend on that engine's package for no reason.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from backend.app.data.emotions import EMOTION_PRESET_VALUES, EmotionName

AvatarEngineErrorKind = Literal[
    "invalid_input",  # bad portrait/audio the engine itself rejects
    "generation_failed",  # the engine ran and produced nothing usable
    "not_available",  # engine not configured/reachable (e.g. no remote endpoint set)
    "cancelled",
]


class AvatarEngineError(Exception):
    """Same `(kind, message)` shape as `InferenceError` and
    `DialectRewriteError` — `api/avatar.py` maps all three through one
    status table, matching the existing convention in `api/tts.py`."""

    def __init__(self, kind: AvatarEngineErrorKind, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class EmotionConfig:
    """The normalized, engine-agnostic emotion representation the brief
    asked for. Every field is a plain 0..1 intensity (blink_rate is a
    multiplier on a natural baseline instead, 1.0 = unchanged) — deliberately
    *not* any one engine's own control vocabulary, so `data/emotions.py`'s
    preset table and the API/frontend never need to know an engine-specific
    string. An `AvatarEngine` implementation maps these onto whatever knobs
    it actually has (or ignores the ones it can't represent — see
    `StubAvatarEngine` for a real example of a deliberately partial mapping).
    """

    expression_strength: float  # overall facial-motion amplitude, 0..1
    head_motion: float  # how much pitch/yaw/roll drift is allowed, 0..1
    blink_rate: float  # multiplier on the engine's natural blink frequency
    eye_motion: float  # gaze/saccade amplitude, 0..1
    smile: float  # baseline mouth-corner lift, independent of lip sync, 0..1

    @classmethod
    def for_emotion(cls, emotion: EmotionName) -> EmotionConfig:
        expr, head, blink, eye, smile = EMOTION_PRESET_VALUES[emotion]
        return cls(expression_strength=expr, head_motion=head, blink_rate=blink, eye_motion=eye, smile=smile)


@dataclass(frozen=True)
class AvatarOptions:
    """Generation controls that are about *how* to render, not *what* to
    express (that's `EmotionConfig`'s job). Kept separate so a future engine
    with more knobs extends this dataclass rather than overloading
    `EmotionConfig` with unrelated fields."""

    fps: int = 25
    max_duration_s: float = 120.0  # see docs/AVATAR_ARCHITECTURE.md "Long audio" section
    # Set by the job manager once a cache/job directory exists — engines
    # write directly into this directory rather than choosing their own
    # location, so `avatar_jobs.py`'s storage-lifecycle/cleanup logic stays
    # authoritative over every file an engine produces. See "Storage" in
    # docs/AVATAR_ARCHITECTURE.md.
    work_dir: Path | None = None
    # (x, y, w, h) from `portrait_validator.validate_portrait()` — a
    # rendering hint, not a requirement every engine uses. Threaded through
    # here rather than re-detected inside each engine so detection happens
    # exactly once per job (at upload time) and every engine agrees on the
    # same box; an engine free of this document just ignores it.
    face_box: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class AvatarResult:
    video_path: Path
    width: int
    height: int
    duration_s: float
    # Per-engine free-form facts worth surfacing in job metadata/logs (e.g.
    # "motion: procedural (no AI lip sync)" for the stub engine) — never
    # user-facing copy on its own, `api/avatar.py`/the job model decide what
    # (if anything) to show.
    engine_notes: list[str]


class AvatarEngine(ABC):
    """One method, deliberately. Portrait validation happens earlier
    (`services/portrait_validator.py`, before a job is even created) and
    audio comes from the existing TTS pipeline (`SpeechPipeline`, untouched
    by this module) — by the time anything calls `generate()`, both inputs
    are already known-good. An engine's only job is turning them into a
    video."""

    #: A short, stable identifier surfaced in job metadata/logs and the
    #: API's `engine` field — e.g. "stub-procedural", "hf-jobs:musetalk".
    name: str

    @abstractmethod
    async def generate(
        self,
        *,
        image_path: Path,
        audio_path: Path,
        emotion: EmotionConfig,
        options: AvatarOptions,
    ) -> AvatarResult:
        """Raises `AvatarEngineError` — never returns a partial/garbage
        result silently, matching `dialect_rewriter.rewrite()` and
        `TTSEngine.generate()`'s own contract."""
        ...
