"""Apply pronunciation rules to text (FR-017).

Pure function over the rule data in `dictionary.py`. Rules are filtered by
locale and provider scope, then applied as whole-word matches so a rule never
fires inside a longer, unrelated word (CHK022) — Arabic attaches prefixes
(و، ف، ب، ل، ك، ال) freely, and a naive substring match would corrupt
unrelated words, which Constitution III forbids.

"Whole word" is defined at the *root* level: known single-letter clitics and
the definite article (ال) are stripped from a token before comparing it to a
rule's `original`, so "العلم" (the-knowledge) matches the "علم" rule while
"معلم" (teacher) — which is not "علم" with any clitic prefix — does not.
"""

from __future__ import annotations

import re

from backend.app.models.tts import PronunciationRule
from backend.app.text_processing.dictionary import RULES

_ARABIC_LETTER = "ء-ي"
_TOKEN = re.compile(f"[{_ARABIC_LETTER}]+")

# Clitics that attach directly to a word with no separator, longest first so
# "بال" and "وال" are stripped before "ب"/"و" alone would partially match.
_CLITIC_PREFIXES = ["بال", "وال", "فال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك"]


def _split_clitic(token: str) -> tuple[str, str]:
    """Return (prefix, root) for the longest recognized clitic prefix, or
    ("", token) if none applies."""
    for prefix in _CLITIC_PREFIXES:
        if token.startswith(prefix) and len(token) > len(prefix):
            return prefix, token[len(prefix):]
    return "", token


def _applicable_rules(locale: str | None, provider: str | None) -> list[PronunciationRule]:
    def matches(rule: PronunciationRule) -> bool:
        if rule.locale is not None and rule.locale != locale:
            return False
        if rule.provider is not None and rule.provider != provider:
            return False
        return True

    return sorted(
        (r for r in RULES if matches(r)), key=lambda r: len(r.original), reverse=True
    )


def _apply_to_arabic_token(token: str, rule: PronunciationRule) -> str:
    """Apply one rule to one Arabic token, respecting clitic prefixes."""
    if token == rule.original:
        return rule.replacement
    prefix, root = _split_clitic(token)
    if prefix and root == rule.original:
        return prefix + rule.replacement
    return token


def apply_pronunciation_rules(
    text: str, *, locale: str | None = None, provider: str | None = None
) -> str:
    rules = _applicable_rules(locale, provider)
    arabic_rules = [r for r in rules if any(_c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" for _c in r.original)]
    other_rules = [r for r in rules if r not in arabic_rules]

    if arabic_rules:

        def _replace_token(m: re.Match[str]) -> str:
            token = m.group(0)
            for rule in arabic_rules:
                if not rule.whole_word:
                    continue
                replaced = _apply_to_arabic_token(token, rule)
                if replaced != token:
                    return replaced
            return token

        text = _TOKEN.sub(_replace_token, text)

    for rule in other_rules:
        if rule.whole_word:
            pattern = re.compile(rf"\b{re.escape(rule.original)}\b")
            text = pattern.sub(rule.replacement, text)
        else:
            text = text.replace(rule.original, rule.replacement)

    return text
