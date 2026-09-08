"""Optional AI dialect rewrite step — OpenAI, opt-in per request.

Everywhere else in this app, `dialect_id` only *steers* pronunciation (the
TTS model's `language` parameter) or diacritizes whatever Arabic the user
already typed (`diacritizer.py`). Neither actually rewrites an MSA-ish
sentence into another dialect's vocabulary/phrasing — that gap is what this
module fills, and only when a request explicitly asks for it
(`TTSRequest.ai_dialect_rewrite` / `PreprocessRequest.ai_dialect_rewrite`).

The same call also handles speaker-gender agreement when the request's
voice `gender` is set (`voice_design` mode only — `None`/auto and `clone`
mode carry no gender to agree with, so it's left alone). Arabic verbs don't
actually inflect by first-person speaker gender, but predicate adjectives,
active participles, and some dialectal first-person forms do ("أنا سعيد" vs
"أنا سعيدة") — real Arabic morphology a regex/rule pass cannot reliably get
right, same reasoning as why dialect rewriting itself needs a model rather
than a dictionary. Scope is deliberately narrow: only words that
grammatically agree with the *speaker referring to themselves* are
adjusted; a second-person addressee or a third person the text talks about
keeps whatever gender the text already gives them, regardless of the
voice's gender — the voice's gender describes who is speaking, not who is
being spoken to or about.

This is the one place in the app that talks to an external, paid API. It is
never required: `is_configured()` reports honestly when `OPENAI_API_KEY`
isn't set (surfaced via `/api/model-info`), and `maybe_rewrite()` is a
straight passthrough — no client built, no network call — whenever a
request doesn't opt in. TTS synthesis itself never depends on this module.

The output is expected to already carry full diacritics for the chosen
dialect. That is deliberate, not accidental: `diacritizer.diacritize()`
already refuses to re-diacritize text that has any diacritic mark at all
(see its module docstring, point 1) and just passes it through, so an
already-diacritized rewrite from here flows untouched through the existing
`text_preprocessor` pipeline — no bypass flag needed anywhere else in the
app for the "use the AI output as-is" requirement.

The prompt below also carries forward `diacritizer.py`'s point 2 (no
classical i'rab case endings for non-MSA dialects, since real dialectal
speech doesn't pronounce them) as an instruction to the model instead of a
post-hoc string strip — there is no local pass left afterward that could do
that stripping for us here.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.data.dialects import DIALECT_BY_ID

logger = logging.getLogger("lahgtna.dialect_rewriter")

DialectRewriteErrorKind = Literal["not_configured", "invalid_input", "upstream_error"]


class DialectRewriteError(Exception):
    """Same `(kind, message)` shape as `inference.InferenceError` — the API
    layer maps both through one `_ERROR_STATUS` table."""

    def __init__(self, kind: DialectRewriteErrorKind, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


class _Rewrite(BaseModel):
    """Structured-output schema for the OpenAI call. Kept to exactly one
    field on purpose: the model's whole job is to hand back one string, not
    to also explain itself — a chatty second field would just be more
    surface area for it to drift on."""

    dialect_text: str


_SYSTEM_PROMPT = (
    "You rewrite a Modern Standard Arabic (or already-dialectal) sentence into "
    "natural, everyday {name_en} Arabic ({name_ar}) — real colloquial vocabulary, "
    "phrasing, and word order a native speaker of that dialect would actually say, "
    "while preserving the original meaning exactly. Do not add or drop information. "
    "Then add full Arabic diacritics (tashkeel) to your rewritten sentence, matching "
    "how it is actually spoken in that dialect: do not add classical grammatical "
    "case-ending diacritics (i'rab) that dialectal speech does not pronounce — only "
    "MSA takes full case endings. If the target is Modern Standard Arabic itself, "
    "keep the wording formal (a near-identity rewrite) and use standard MSA "
    "diacritics including case endings. "
    "{gender_clause}"
    "Respond with only the rewritten, diacritized Arabic text — no explanation, "
    "no quotes, no transliteration, nothing else."
)

# Only inserted when the request has an explicit voice gender (voice_design
# mode with male/female chosen — never for "auto"/None or clone mode, which
# have no gender to agree with). Scope is deliberately narrow — see module
# docstring for why only self-reference is touched.
_GENDER_CLAUSE = (
    "The voice speaking this sentence is grammatically {gender}. Any word that "
    "grammatically agrees with the SPEAKER referring to themselves in first person — "
    "predicate adjectives, active participles, and any first-person verb or "
    "colloquial form that does inflect by gender in this dialect — must agree with "
    "a {gender} speaker, regardless of what gender the original text used. Do NOT "
    "change the grammatical gender of anyone else the sentence addresses or "
    "describes: a second-person 'you' or a third person stays exactly whatever "
    "gender the original text already gives them. "
)

# Guards against a degenerate/unbounded response — not a security boundary
# (this is the user's own text coming back), just a sanity cap so a stuck
# generation can't balloon into an unusably long TTS input.
_MAX_OUTPUT_RATIO = 4


def is_configured() -> bool:
    """No network call — just whether the optional credential is set.
    Used by `/api/model-info` so the frontend can grey out the toggle with
    an honest reason instead of only failing at request time."""
    return bool(get_settings().openai_api_key)


@lru_cache(maxsize=1)
def _client():
    """Built once, lazily — importing `openai` and constructing a client
    at module import time would make every caller of this module (even
    ones that never opt in) pay that cost."""
    from openai import AsyncOpenAI

    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_s,
        max_retries=2,
    )


async def rewrite(text: str, *, dialect_id: str, gender: str | None = None) -> str:
    """Calls OpenAI once and returns the rewritten, diacritized Arabic text
    (also speaker-gender-agreed when `gender` is given — see module
    docstring). Raises `DialectRewriteError` — never returns a partial/
    garbage result silently. No request text or model output is ever
    logged (matches `main.py`'s "no request text or generated audio is
    ever logged" policy for the rest of the app)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise DialectRewriteError(
            "not_configured", "AI dialect rewrite requires OPENAI_API_KEY to be set on the server"
        )

    dialect = DIALECT_BY_ID.get(dialect_id)
    name_en = dialect.name_en if dialect else dialect_id
    name_ar = dialect.name_ar if dialect else dialect_id
    gender_clause = _GENDER_CLAUSE.format(gender=gender) if gender else ""

    try:
        response = await _client().responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT.format(name_en=name_en, name_ar=name_ar, gender_clause=gender_clause),
                },
                # The user's own text, kept out of the instruction channel —
                # just data to transform, not something that can redefine
                # the task above (AGENTS.md: never interpolate untrusted
                # data into system/developer instructions).
                {"role": "user", "content": text},
            ],
            text_format=_Rewrite,
            # Measured directly against the real API while building this:
            # gpt-5-mini's default reasoning effort took 15-40s on this
            # trivial rewrite/diacritize task — enough to blow past
            # `openai_timeout_s` on a non-trivial fraction of requests.
            # "minimal" cut that to ~1-3s but was measurably unreliable
            # (~1 in 3 sampled calls returned two stacked sentence variants
            # or a stray control character in the field) — "low" measured
            # clean across the same repeated sampling at ~2-12s, a real
            # trade of some latency for output the app can actually trust.
            # `_sanitize()` below is still the real backstop either way —
            # effort level is a reliability *lever*, not a correctness
            # guarantee for an LLM's output.
            reasoning={"effort": "low"},
        )
    except Exception as exc:  # noqa: BLE001 - any OpenAI SDK/network failure (timeout, rate limit, ...)
        logger.warning("Dialect rewrite request failed (%s)", type(exc).__name__)
        raise DialectRewriteError("upstream_error", "AI dialect rewrite failed — try again in a moment") from exc

    parsed = response.output_parsed
    raw = parsed.dialect_text if parsed else ""
    result = _sanitize(raw)
    if not result:
        raise DialectRewriteError("invalid_input", "AI dialect rewrite returned no usable text")
    if len(result) > _MAX_OUTPUT_RATIO * max(len(text), 1):
        raise DialectRewriteError("invalid_input", "AI dialect rewrite returned an unexpectedly long result")
    return result


# C0/C1 control characters, excluding the plain whitespace ones ('\t', '\n')
# that `_sanitize` still needs to see to detect the multi-line failure mode
# below. Stray control bytes were observed directly in real responses at
# low sampling (e.g. a trailing U+000F) — structured-output JSON validity
# says nothing about whether the *string inside* is clean.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize(raw: str) -> str:
    """Defends against two real, reproduced failure modes of this call that
    a valid JSON schema does nothing to prevent: (1) stray control-byte
    artifacts appended to an otherwise-fine string, and (2) the model
    hedging with *two* stacked sentence variants (typically one MSA-flavored,
    one dialectal) in the single `dialect_text` field, separated by a
    newline — which would otherwise flow straight into TTS and get spoken
    twice, back to back, with no indication anything was wrong.

    (2) is deliberately *not* repaired by picking one line — there is no
    reliable way to know which line is the intended one, and shipping a
    guess is worse than the caller (maybe_rewrite -> the API layer) turning
    it into a normal `invalid_input` the user can just retry."""
    cleaned = _CONTROL_CHAR_RE.sub("", raw).strip()
    lines = [line for line in cleaned.splitlines() if line.strip()]
    if len(lines) > 1:
        raise DialectRewriteError(
            "invalid_input", "AI dialect rewrite returned more than one sentence variant"
        )
    return lines[0].strip() if lines else ""


async def maybe_rewrite(
    text: str, *, dialect_id: str, enabled: bool, gender: str | None = None
) -> tuple[str, list[str]]:
    """The one function every caller uses. Returns `(text, [])` unchanged —
    no client built, no network call — when `enabled` is False, so opting
    out costs nothing anywhere in the request path. `gender` (from the
    request's voice_design gender, or None for auto/clone) is folded into
    the same call rather than a second one — see module docstring."""
    if not enabled:
        return text, []
    rewritten = await rewrite(text, dialect_id=dialect_id, gender=gender)
    dialect = DIALECT_BY_ID.get(dialect_id)
    label = dialect.name_en if dialect else dialect_id
    note = f"Text rewritten for {label}"
    if gender:
        note += f" ({gender} voice)"
    note += f" via OpenAI ({get_settings().openai_model}) before synthesis."
    return rewritten, [note]
