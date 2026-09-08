"""Script-based Arabic/English segmentation — no model, no LLM call.

Per-character Unicode block detection classifies each whitespace-delimited
token as Arabic, English (Latin-script), or neutral (bare digits/punctuation
with no letters at all — a lone number, a dash, a URL's `://`, etc.).
Neutral tokens are then resolved onto a real language before merging
consecutive same-language tokens into segments:

- A neutral token touching an Arabic-tagged neighbor on either side joins
  Arabic — this app's whole surface is Arabic-primary, and a bare number or
  piece of punctuation inside an Arabic sentence reads as Arabic punctuation,
  not English.
- Otherwise it joins whichever neighbor exists (preferring the one before
  it), so "iPhone 15 Pro" stays one English run rather than splitting on the
  number.

This resolves the exact worked example from the spec:
`"مرحبا React developer كيفك"` -> `[("ar","مرحبا "), ("en","React developer"),
("ar"," كيفك")]` — both surrounding spaces bind to their Arabic neighbor,
and the two English words merge into one run instead of two.

A token is classified by its own dominant script, so compound tokens with no
internal whitespace stay intact as one unit: `"React.js"`, `"FastAPI"`,
`"GPT-5"`, `"https://example.com"`, `"user@example.com"` are each one
English token (never split mid-token), and acronyms (`"API"`, `"UI"`,
`"AWS"`) fall out naturally as short all-Latin tokens — no acronym list
needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Language = Literal["ar", "en"]
_TokenTag = Literal["ar", "en", "neutral"]

# Arabic letter ranges only (not the wider diacritics-included range used by
# diacritizer.py) — a diacritic mark alone shouldn't tip a token's script.
_ARABIC_LETTER_RE = re.compile(
    "[ء-غف-يٱ-ۓەݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
)
_TOKEN_RE = re.compile(r"\S+|\s+")


@dataclass(frozen=True)
class Segment:
    language: Language
    text: str


def _classify_token(token: str) -> _TokenTag:
    if token.isspace():
        return "neutral"
    ar_count = len(_ARABIC_LETTER_RE.findall(token))
    en_count = sum(1 for ch in token if ch.isascii() and ch.isalpha())
    if ar_count == 0 and en_count == 0:
        return "neutral"
    return "ar" if ar_count >= en_count else "en"


def segment_languages(text: str) -> list[Segment]:
    """Split `text` into consecutive Arabic/English runs.

    Empty input returns an empty list. Whitespace-only or fully-neutral
    input (bare digits/punctuation) resolves to a single Arabic segment —
    this app has no non-Arabic default context to fall back to.
    """
    if not text:
        return []

    tokens = _TOKEN_RE.findall(text)
    tags: list[_TokenTag] = [_classify_token(t) for t in tokens]
    n = len(tags)
    resolved: list[Language] = []

    for i, tag in enumerate(tags):
        if tag != "neutral":
            resolved.append(tag)
            continue
        left = next((tags[j] for j in range(i - 1, -1, -1) if tags[j] != "neutral"), None)
        right = next((tags[j] for j in range(i + 1, n) if tags[j] != "neutral"), None)
        if left == "ar" or right == "ar":
            resolved.append("ar")
        elif left is not None:
            resolved.append(left)
        elif right is not None:
            resolved.append(right)
        else:
            resolved.append("ar")  # whole text is neutral — default to Arabic

    segments: list[Segment] = []
    current_lang: Language | None = None
    buffer: list[str] = []
    for token, lang in zip(tokens, resolved):
        if lang != current_lang and buffer:
            segments.append(Segment(current_lang, "".join(buffer)))  # type: ignore[arg-type]
            buffer = []
        current_lang = lang
        buffer.append(token)
    if buffer:
        segments.append(Segment(current_lang, "".join(buffer)))  # type: ignore[arg-type]

    return segments
