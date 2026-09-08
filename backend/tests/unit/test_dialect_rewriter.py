"""Unit tests for the AI dialect rewrite step — the real OpenAI API is
never called here; `_client()` is monkeypatched with a fake client so these
stay fast, offline, and free (see backend/tests/integration/test_live_model.py
for the equivalent pattern applied to a real model instead of a mock)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app.config import Settings
from backend.app.services import dialect_rewriter


def _settings(*, api_key: str | None = "sk-test-key") -> Settings:
    return Settings(openai_api_key=api_key, openai_model="gpt-5-mini", openai_timeout_s=5.0)


@dataclass
class _FakeParsed:
    dialect_text: str


@dataclass
class _FakeResponse:
    output_parsed: _FakeParsed | None


class _FakeResponses:
    def __init__(self, *, result: str | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return _FakeResponse(output_parsed=_FakeParsed(dialect_text=self._result) if self._result is not None else None)


class _FakeClient:
    def __init__(self, *, result: str | None = None, error: Exception | None = None) -> None:
        self.responses = _FakeResponses(result=result, error=error)


async def test_maybe_rewrite_disabled_is_a_pure_passthrough(monkeypatch):
    def boom():
        raise AssertionError("no client should be built when enabled=False")

    monkeypatch.setattr(dialect_rewriter, "_client", boom)
    text, warnings = await dialect_rewriter.maybe_rewrite("مرحبا", dialect_id="saudi", enabled=False)
    assert text == "مرحبا"
    assert warnings == []


def test_is_configured_reflects_settings(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", lambda: _settings(api_key="sk-test-key"))
    assert dialect_rewriter.is_configured() is True

    monkeypatch.setattr(dialect_rewriter, "get_settings", lambda: _settings(api_key=None))
    assert dialect_rewriter.is_configured() is False


async def test_rewrite_without_api_key_raises_not_configured(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", lambda: _settings(api_key=None))
    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        await dialect_rewriter.maybe_rewrite("مرحبا", dialect_id="saudi", enabled=True)
    assert exc_info.value.kind == "not_configured"


async def test_rewrite_success_returns_parsed_text_and_warns(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="هلا وربع، كيفك اليوم؟")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    text, warnings = await dialect_rewriter.maybe_rewrite("مرحبا، كيف حالك اليوم؟", dialect_id="saudi", enabled=True)

    assert text == "هلا وربع، كيفك اليوم؟"
    assert len(warnings) == 1
    assert "Saudi" in warnings[0]
    assert "gpt-5-mini" in warnings[0]

    # The user's text travels as data (the user message), never folded into
    # the fixed system instructions.
    call = fake_client.responses.calls[0]
    assert call["input"][0]["role"] == "system"
    assert call["input"][1] == {"role": "user", "content": "مرحبا، كيف حالك اليوم؟"}


async def test_rewrite_upstream_failure_is_sanitized(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(error=RuntimeError("connection reset talking to sk-test-key-leaked"))
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        await dialect_rewriter.rewrite("مرحبا", dialect_id="saudi")

    assert exc_info.value.kind == "upstream_error"
    assert "sk-test-key" not in exc_info.value.message


async def test_rewrite_empty_output_raises_invalid_input(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="   ")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        await dialect_rewriter.rewrite("مرحبا", dialect_id="saudi")
    assert exc_info.value.kind == "invalid_input"


async def test_rewrite_wildly_long_output_raises_invalid_input(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="مرحبا " * 500)  # way past 4x the (short) input
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        await dialect_rewriter.rewrite("مرحبا", dialect_id="saudi")
    assert exc_info.value.kind == "invalid_input"


# Real, reproduced failure modes of the live API — see dialect_rewriter._sanitize's
# docstring. Structured-output JSON validity guarantees a string field exists;
# it says nothing about what's actually inside it.


def test_sanitize_strips_stray_control_characters():
    assert dialect_rewriter._sanitize("مرحبا\x0f") == "مرحبا"
    assert dialect_rewriter._sanitize("مرحبا\x00") == "مرحبا"


def test_sanitize_rejects_two_stacked_sentence_variants():
    # Real reproduced case: the model hedged with an MSA-flavored line and
    # a dialectal line for the same sentence, newline-separated, both
    # inside the one `dialect_text` field. Picking one silently would be a
    # guess — this must raise so the caller gets a normal, retryable error
    # instead of TTS reading both variants back to back.
    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        dialect_rewriter._sanitize("تقدر تساعدني؟\nتَقْدَرْ تُساعِدْنِي؟")
    assert exc_info.value.kind == "invalid_input"


def test_sanitize_tolerates_a_single_trailing_blank_line():
    assert dialect_rewriter._sanitize("مرحبا\n") == "مرحبا"
    assert dialect_rewriter._sanitize("مرحبا\n\n") == "مرحبا"


async def test_rewrite_rejects_multi_line_output_from_the_api(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="تقدر تساعدني؟\nتَقْدَرْ تُساعِدْنِي؟")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    with pytest.raises(dialect_rewriter.DialectRewriteError) as exc_info:
        await dialect_rewriter.rewrite("تقدر تساعدني؟", dialect_id="egyptian")
    assert exc_info.value.kind == "invalid_input"


async def test_rewrite_strips_stray_control_characters_from_the_api(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="تقدر تساعدني؟\x0f")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    result = await dialect_rewriter.rewrite("تقدر تساعدني؟", dialect_id="egyptian")
    assert result == "تقدر تساعدني؟"


# Speaker-gender agreement — folded into the same call, only when the
# request's voice gender is known (never for auto/clone). See module
# docstring: only the speaker's own self-reference is meant to be touched.


async def test_rewrite_without_gender_omits_the_gender_clause(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="مرحبا")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    await dialect_rewriter.rewrite("مرحبا", dialect_id="saudi")  # gender defaults to None

    system_content = fake_client.responses.calls[0]["input"][0]["content"]
    assert "The voice speaking this sentence is grammatically" not in system_content


async def test_rewrite_with_gender_includes_a_scoped_gender_clause(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="مرحبا")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    await dialect_rewriter.rewrite("مرحبا", dialect_id="saudi", gender="female")

    system_content = fake_client.responses.calls[0]["input"][0]["content"]
    assert "female" in system_content
    # The scope restriction — never touch the addressee/third party — must
    # actually be present, not just the gender word itself.
    assert "second-person" in system_content or "addresses or" in system_content


async def test_maybe_rewrite_passes_gender_through(monkeypatch):
    monkeypatch.setattr(dialect_rewriter, "get_settings", _settings)
    fake_client = _FakeClient(result="مرحبا")
    monkeypatch.setattr(dialect_rewriter, "_client", lambda: fake_client)

    text, warnings = await dialect_rewriter.maybe_rewrite(
        "مرحبا", dialect_id="saudi", enabled=True, gender="male"
    )
    system_content = fake_client.responses.calls[0]["input"][0]["content"]
    assert "male" in system_content
    assert any("male" in w for w in warnings)
