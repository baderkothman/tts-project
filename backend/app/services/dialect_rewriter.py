"""Optional AI dialect rewrite step — OpenAI, automatic whenever configured.

Everywhere else in this app, `dialect_id` only *steers* pronunciation (the
TTS model's `language` parameter) or diacritizes whatever Arabic the user
already typed (`diacritizer.py`). Neither actually rewrites an MSA-ish
sentence into another dialect's vocabulary/phrasing — that gap is what this
module fills.

Not a per-request opt-in (there used to be a `TTSRequest.ai_dialect_rewrite`
/ `AvatarGenerationRequest.ai_dialect_rewrite` toggle; both were removed).
It now runs automatically, gated only on `is_configured()` (whether
`OPENAI_API_KEY` is set server-side) — every `/api/tts`, `/api/tts/stream`,
and avatar generation call gets it for free when the key is set, and it's
silently skipped when it isn't. The one place it deliberately never runs is
`/api/preprocess` (the live "what will be spoken" preview as the user
types/picks a dialect) — see that endpoint's own docstring: calling a paid
external API on every keystroke or dialect change would be real,
unnecessary cost, so the rewrite is scoped to actual generation requests
only, triggered once per "generate" click, not per input change.

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

Embedded English (or other Latin-script) words are deliberately left
untouched — never translated, and (after a brief detour) never
transliterated into Arabic letters either. An earlier iteration of this
prompt *did* ask the model to convert embedded English into Arabic-script
phonetic spelling (e.g. "meeting" -> "ميتنج"), on the theory that it would
read more naturally next to conventional Arabic spellings of common
loanwords. Direct user feedback reversed that: English words should stay
exactly as typed, in Latin script. That's also the one already-existing
behavior for mixed-language text everywhere else in the app —
`text_preprocessor.py`'s `native` pipeline mode already leaves English
segments untouched (only `pipeline_mode="transliteration"`, which the
frontend does not currently expose, converts English at all, via a
separate rule-based pass in `services/transliterator.py`) — so this module
no longer needs to do anything special with English; it simply doesn't
rewrite or diacritize what isn't Arabic.

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

The prompt asks the model for `diacritizer.py`'s same point 2 (no classical
i'rab case endings for non-MSA dialects, since real dialectal speech
doesn't pronounce them) directly, but a prompt is a request, not a
guarantee — sampled live traffic showed the model sometimes complies only
partially (a correctly-stripped sentence with one stray case ending left on
a word, or occasionally the full MSA case-ending pattern reappearing
outright). `_sanitize()` below therefore reapplies
`diacritizer.strip_dialectal_case_endings()` — the exact same deterministic
rule the local (non-AI) pipeline already enforces — to every non-MSA
rewrite, regardless of what the model actually did. This is the one place
in the pipeline where the model's own diacritization is not simply trusted
as final: everything else about the rewrite (wording, vocabulary, which
words even get diacritics) is still entirely the model's output.

`_sanitize()` also catches a rewrite that leaves any real Arabic word
completely bare (no diacritic marks at all) while the rest of the sentence
is vocalized — a real, reproduced partial-diacritization failure mode,
distinct from the case-ending issue above. Unlike that one, this failure
*is* repairable without another round trip to the model: this app already
has a local diacritizer (`diacritizer.diacritize()`) sitting right there
for the non-AI path, and it works just as well on a single bare word
mid-sentence as it does on a whole undiacritized input — `_repair_bare_words()`
below runs exactly that. An earlier version of this behavior instead raised
an error and left `rewrite()` to retry the whole API call once before
giving up, which meant a persistent case (the model reliably mis-handling
one particular word) surfaced as a visible failure to the user instead of
getting fixed. `rewrite()` still retries (twice, as of 2026-09) for the one
failure mode that genuinely has no local fix — the model hedging with two
stacked sentence variants (see failure mode 2 above). The system prompt now
also explicitly forbids offering more than one variant in the first place;
the retries are a safety net on top of that instruction, not a replacement
for it.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.data.dialects import DIALECT_BY_ID
from backend.app.services import diacritizer

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
    "If the input contains any English (or other Latin-script) words, names, or "
    "phrases, leave them exactly as they are, written in English/Latin script — do "
    "NOT translate them and do NOT transliterate them into Arabic letters. Only the "
    "surrounding Arabic wording is yours to rewrite; any embedded Latin-script text "
    "passes through completely untouched, unchanged, in its original spelling. "
    "Then add full Arabic diacritics (tashkeel) to every word of the Arabic portion "
    "of the rewritten sentence — every single letter that takes a vowel must carry "
    "one, including a sukūn on a letter that carries no vowel at all; never leave "
    "any Arabic word without diacritics while others around it have them. Diacritics "
    "must match how the sentence is actually spoken in that dialect: never place a "
    "classical grammatical case-ending diacritic (i'rab) — a final damma, kasra, "
    "fatha, or any tanween that marks grammatical case — on the last letter of a "
    "word, since dialectal speech does not pronounce these; only Modern Standard "
    "Arabic takes full case endings. The last letter of most words should instead "
    "carry a sukūn, or whatever short vowel is actually pronounced there in that "
    "dialect, never a grammatical case marker. Do not add diacritics to any "
    "Latin-script word — it stays exactly as written. "
    "If the target is Modern Standard Arabic itself, keep the wording formal (a "
    "near-identity rewrite) and use standard MSA diacritics including case endings. "
    "{gender_clause}"
    "Give exactly one rewritten sentence. Never offer more than one phrasing, option, "
    "or variant, and never present a fallback alongside a preferred version — if more "
    "than one wording would sound natural, silently choose the single best one "
    "yourself and commit to it. "
    "Respond with only that one rewritten, diacritized Arabic text — no explanation, "
    "no quotes, no alternate versions, nothing else."
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
    """No network call — just whether the optional credential is set. This
    is the *only* gate on whether the automatic rewrite runs (see module
    docstring) — `speech_pipeline.py` and `avatar_jobs.py` both call this
    directly as `maybe_rewrite()`'s `enabled` argument. Also surfaced via
    `/api/model-info` (`dialect_rewriter_configured`) so callers can tell,
    informationally, whether a given deployment will apply it."""
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

    prompt = _SYSTEM_PROMPT.format(name_en=name_en, name_ar=name_ar, gender_clause=gender_clause)

    async def _call() -> str:
        try:
            response = await _client().responses.parse(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": prompt},
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
        return parsed.dialect_text if parsed else ""

    # Up to three attempts total, but the retry only fires for a
    # content-quality problem (empty output, a multi-line hedge, or a word
    # left completely bare of diacritics) — a sporadic generation glitch
    # worth trying again, not a systematic failure. Transport-level
    # failures (`upstream_error`, raised inside `_call` above) are never
    # retried here: the OpenAI client already retries those itself
    # (`max_retries=2` on the client in `_client()`), and a further attempt
    # after a timeout would just multiply the wait for something not caused
    # by the response content at all.
    #
    # Bumped from two attempts to three (2026-09) after the multi-line-hedge
    # failure mode was observed twice back to back in real use — one retry
    # wasn't enough headroom on its own. The real fix is the system prompt
    # now explicitly forbidding multiple variants (see _SYSTEM_PROMPT); this
    # extra attempt is defense in depth on top of that, not a substitute for
    # it — it only costs latency on the failure path, never the common case.
    last_error: DialectRewriteError | None = None
    for attempt in range(3):
        try:
            result = _sanitize(await _call(), dialect_id=dialect_id)
        except DialectRewriteError as exc:
            if exc.kind != "invalid_input":
                raise
            last_error = exc
            continue
        if not result:
            last_error = DialectRewriteError("invalid_input", "AI dialect rewrite returned no usable text")
            continue
        if len(result) > _MAX_OUTPUT_RATIO * max(len(text), 1):
            raise DialectRewriteError("invalid_input", "AI dialect rewrite returned an unexpectedly long result")
        return result
    assert last_error is not None  # loop only exits without returning by hitting `continue` at least once
    raise last_error


# C0/C1 control characters, excluding the plain whitespace ones ('\t', '\n')
# that `_sanitize` still needs to see to detect the multi-line failure mode
# below. Stray control bytes were observed directly in real responses at
# low sampling (e.g. a trailing U+000F) — structured-output JSON validity
# says nothing about whether the *string inside* is clean.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# A word is "real Arabic content" worth checking for diacritics once it has
# at least this many Arabic letters — short 1-2 letter function words
# (و "and", بـ/لـ-prefixed particles) are sometimes left unmarked even by a
# fully-vocalized rendering, so checking those would produce false
# positives on otherwise-correct output.
_MIN_LETTERS_FOR_DIACRITIC_CHECK = 3
_ARABIC_LETTER_RE = re.compile("[ء-ي]")


def _is_bare_word(word: str) -> bool:
    return len(_ARABIC_LETTER_RE.findall(word)) >= _MIN_LETTERS_FOR_DIACRITIC_CHECK and not diacritizer.has_diacritics(
        word
    )


def _repair_bare_words(text: str, *, dialect_id: str) -> str:
    """Fixes failure mode (3) from `_sanitize`'s docstring: a word the AI
    rewrite left completely undiacritized while the rest of the sentence
    was fully vocalized. There *is* a diacritic source available for a
    single bare word from outside the model that generated it — the local
    Fine-Tashkeel diacritizer this app already runs for the non-AI path.
    `diacritizer.diacritize()` only refuses to touch text that *already*
    has a diacritic somewhere in it (see its own module docstring) — a
    genuinely bare word has none, so it runs normally, including this same
    dialect's i'rab (case-ending) stripping. An earlier version of this
    function gave up and raised an error here instead, surfacing a visible
    failure to the user for something this app had the means to just fix."""
    return " ".join(
        diacritizer.diacritize(word, dialect_id=dialect_id)[0] if _is_bare_word(word) else word
        for word in text.split(" ")
    )


def _sanitize(raw: str, *, dialect_id: str = "msa") -> str:
    """Defends against three real, reproduced failure modes of this call
    that a valid JSON schema does nothing to prevent:

    1. Stray control-byte artifacts appended to an otherwise-fine string.
    2. The model hedging with *two* stacked sentence variants (typically one
       MSA-flavored, one dialectal) in the single `dialect_text` field,
       separated by a newline — which would otherwise flow straight into
       TTS and get spoken twice, back to back, with no indication anything
       was wrong. Deliberately *not* repaired by picking one line — there
       is no reliable way to know which line is the intended one, and
       shipping a guess is worse than the caller (`rewrite`'s retry, then
       `maybe_rewrite` -> the API layer) turning it into a normal
       `invalid_input` that gets one automatic retry.
    3. A rewrite that fully diacritizes most of the sentence but leaves one
       or more real Arabic words completely bare — a partial-diacritization
       glitch distinct from (2). Unlike (2), this one *is* repairable
       without another round trip to the model: `_repair_bare_words` below
       runs the bare word(s) through this app's own local diacritizer
       instead. An earlier version of this function raised an error here
       the same way as (2) — visibly failing a request over something this
       app already had the tooling to just fix.

    For any non-MSA dialect, this is also where the deterministic i'rab
    (case-ending) backstop from `diacritizer.py` gets applied to the rest
    of the sentence — see this module's docstring for why the prompt's own
    instruction not to use case endings isn't trusted as sufficient on its
    own."""
    cleaned = _CONTROL_CHAR_RE.sub("", raw).strip()
    lines = [line for line in cleaned.splitlines() if line.strip()]
    if len(lines) > 1:
        raise DialectRewriteError(
            "invalid_input", "AI dialect rewrite returned more than one sentence variant"
        )
    result = lines[0].strip() if lines else ""
    if not result:
        return result

    if any(_is_bare_word(word) for word in result.split(" ")):
        result = _repair_bare_words(result, dialect_id=dialect_id)

    if dialect_id != "msa":
        result = diacritizer.strip_dialectal_case_endings(result)
    return result


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
