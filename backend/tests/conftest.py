"""Suite-wide fixtures — applies to every test under backend/tests (unit,
contract, integration alike; pytest auto-discovers a conftest.py at the root
of `testpaths` regardless of which subdirectory a test lives in)."""

from __future__ import annotations

import pytest

from backend.app.config import Settings
from backend.app.services import dialect_rewriter


@pytest.fixture(autouse=True)
def _dialect_rewriter_not_configured_by_default(monkeypatch):
    """The AI dialect rewrite step is now automatic — gated only on
    `dialect_rewriter.is_configured()` (i.e. the real, `@lru_cache`d,
    `.env`-backed `Settings().openai_api_key`), never on a per-request flag
    (see `dialect_rewriter.py`'s module docstring for why that changed).

    Without this fixture, every test that exercises `SpeechPipeline.synthesize()`
    or `avatar_jobs.py`'s `_run_job` — even ones with nothing to do with
    dialect rewriting — would silently pick up whatever real `OPENAI_API_KEY`
    happens to be sitting in this machine's own `.env` (developers need one
    set locally to exercise the feature at all) and attempt a real, paid,
    network-dependent OpenAI call. That's exactly what AGENTS.md §8 forbids
    ("Do not make live paid model calls in the default unit-test suite") —
    and it's what actually happened once here, hanging most of the suite on
    real network calls the sandbox couldn't complete.

    Defaults every test to "not configured" (a real `Settings` instance with
    `openai_api_key` forced to `None` — the exact `_settings(api_key=None)`
    shape `test_dialect_rewriter.py` already uses per-test) so no test
    depends on ambient machine state. A test that specifically wants to
    exercise the "configured" path — `dialect_rewriter.is_configured()` is
    `True` — simply monkeypatches `dialect_rewriter.get_settings` (or
    `is_configured`/`maybe_rewrite`/`rewrite` directly) itself; monkeypatch's
    per-test `setattr` naturally overrides whatever this fixture set."""
    monkeypatch.setattr(dialect_rewriter, "get_settings", lambda: Settings(openai_api_key=None))
