"""Splits already-processed, pronunciation-ready text into sentence-level
chunks for streamed synthesis (`speech_pipeline.SpeechPipeline.synthesize_stream`).

This exists for one reason: `OmniVoice.generate()` is a blocking call that
returns the *entire* clip's audio only once every requested token is
decoded — there is no token-level streaming API on the installed package
(verified by reading `omnivoice.OmniVoice`'s public surface: `generate` is
the only synthesis entry point, and its return type is a fully materialized
`list[np.ndarray]`, not a generator). The only lever this project actually
has for a meaningful "time to first audio" is calling `generate()` more than
once, on smaller pieces of text, and returning each piece's audio as soon as
it's ready instead of waiting for the whole request. Splitting on sentence
boundaries (rather than e.g. fixed character counts) keeps each chunk a
prosodically coherent unit for the model, rather than cutting mid-clause.

Deliberately simple, not a sentence tokenizer: regex on Arabic/Latin
terminators (`. ! ? ؟ ؛`) plus newlines. Two things this gets right without
extra logic, and one honest gap:

- A decimal point ("3.14") is never split, because the regex only splits a
  terminator that is *followed by whitespace* — "3." is followed by "1", a
  digit, not whitespace.
- A two-letter Arabic abbreviation with an internal period ("د.إ", dirham)
  is never split for the same reason — the period sits *inside* the token,
  not before whitespace.
- What is NOT handled: a terminating abbreviation immediately followed by
  more sentence text ("... الخ. وبعده ..." — "etc." followed by continuing
  prose) will still split there, same as it would for "etc. " in English —
  no abbreviation dictionary is consulted. Splitting one sentence into two
  synthesis calls in that rare case costs a fraction of a second of extra
  latency and a slightly premature pause; it does not lose or corrupt text
  the way the diacritizer's old whole-blob generation cap did.
"""

from __future__ import annotations

import re

_TERMINATORS = ".!?؟؛"
# Split right after a terminator that's followed by whitespace, or on any
# run of newlines (a blank line is always a real boundary, terminator or not).
_SPLIT_RE = re.compile(rf"(?<=[{_TERMINATORS}])\s+(?=\S)|\n+")

# A bare leftover terminator (or anything this short) makes for a wasteful,
# audibly clipped synthesis call on its own — fold it back into its neighbor
# instead of sending the model a one-character "sentence".
_MIN_CHUNK_CHARS = 2


def split_sentences(text: str) -> list[str]:
    """Returns non-empty sentence-ish chunks in original order. Empty/blank
    input returns an empty list."""
    if not text.strip():
        return []

    raw = [p.strip() for p in _SPLIT_RE.split(text)]
    raw = [p for p in raw if p]
    if not raw:
        return []

    merged: list[str] = []
    for piece in raw:
        if merged and len(piece) < _MIN_CHUNK_CHARS:
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return merged
