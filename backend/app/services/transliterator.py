"""English -> Arabic-script phonetic transliteration — the last-resort
fallback (priority 3 of 3; `english_tts.py`'s docstring explains why the
dual-model path is preferred whenever it's available and worked in
testing).

This is deliberately **not** a letter-by-letter spelling transliteration —
`development` is never walked d-e-v-e-l-o-p-m-e-n-t. It phonemizes the
English text with `espeak-ng` (via `phonemizer`, already a dependency of
`english_tts.py`'s Kokoro pipeline — one phonemization backend for the
whole English path, not two), then maps each IPA phoneme to the Arabic
letter that best approximates its sound. `espeak-ng`'s G2P is rule-based
and covers arbitrary English spelling, including compounds with no
dictionary entry ("FastAPI" -> "fast" + "API" spelled out, "TypeScript" ->
"type" + "script") and bare acronyms ("API" -> "eɪ p iː aɪ", i.e. spelled
by letter name) — verified directly against espeak's own output for the
exact terms in this project's test set (`react`, `python`, `development`,
`meeting`, `github`, `typescript`, `fastapi`, `vercel`, `api`), not assumed.

This is still an approximation: unstressed vowels are simplified or
dropped the way real Arabic loanword transliteration usually does, so
results are readable and close to common usage ("react" -> "رياكت",
matching the task brief's own example) but won't always match one
specific popular spelling. `pronunciation_dictionary.py` is the intended
escape hatch for any term this gets wrong.
"""

from __future__ import annotations

import re
import threading

from phonemizer.backend import EspeakBackend
from phonemizer.separator import Separator

# IPA (espeak-ng, en-us) -> Arabic letter, by sound. Multi-character
# symbols first so a naive longest-match isn't needed — phonemizer already
# hands us one token per phone when `separator.phone` is set.
_VOWELS = {
    "iː": "ي", "ɪ": "ي", "i": "ي", "ᵻ": "ي", "e": "ي", "ɛ": "ي",
    "æ": "ا", "ɑː": "ا", "ɑ": "ا", "ʌ": "ا",
    "ɒ": "و", "ɔː": "و", "ɔ": "و", "ʊ": "و", "uː": "و", "u": "و",
    "ɜː": "ر", "ɜ": "ر", "ɚ": "ر",
    "ə": "",  # unstressed schwa — a distinct IPA symbol from ʌ, always reduced/silent-ish
    "eɪ": "اي", "aɪ": "اي", "ɔɪ": "وي", "aʊ": "او", "oʊ": "و", "əʊ": "و",
}

_CONSONANTS = {
    "p": "ب", "b": "ب", "t": "ت", "d": "د", "k": "ك", "ɡ": "ج", "g": "ج",
    "tʃ": "تش", "dʒ": "ج", "f": "ف", "v": "ڤ", "θ": "ث", "ð": "ذ",
    "s": "س", "z": "ز", "ʃ": "ش", "ʒ": "ج", "h": "ه", "m": "م", "n": "ن",
    "ŋ": "نج", "l": "ل", "ɹ": "ر", "r": "ر", "j": "ي", "w": "و", "ɾ": "ت",
}

_PHONEME_MAP = {**_VOWELS, **_CONSONANTS}
# Longest-symbol-first, for the greedy scan in `_phones_to_arabic`: espeak
# glues some phones together with no separating space even when phone-level
# separation is requested (a syllabic consonant like "l" after a dropped
# schwa comes back as one token "əl"; a lengthened vowel like "ɜː" is two
# Unicode characters with no space between them) — so this walks the raw
# character stream rather than trusting whitespace to delimit phones.
_SYMBOLS_LONGEST_FIRST = sorted(_PHONEME_MAP, key=len, reverse=True)

_WORD_RE = re.compile(r"[A-Za-z]+|[^A-Za-z]+")


def _is_latin_word(piece: str) -> bool:
    # str.isalpha() is true for Arabic letters too — this must check
    # specifically for the Latin-word half of the split, not "any letter".
    return piece[:1].isascii() and piece[:1].isalpha()

_lock = threading.Lock()
_backend: EspeakBackend | None = None


def _get_backend() -> EspeakBackend:
    global _backend
    with _lock:
        if _backend is None:
            try:
                from phonemizer.backend.espeak.wrapper import EspeakWrapper

                for candidate in (
                    "/opt/homebrew/lib/libespeak-ng.dylib",
                    "/usr/local/lib/libespeak-ng.dylib",
                    "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",
                    "/usr/lib/libespeak-ng.so.1",
                ):
                    try:
                        EspeakWrapper.set_library(candidate)
                        break
                    except Exception:  # noqa: BLE001 - try the next candidate path
                        continue
            except Exception:  # noqa: BLE001 - fall through, EspeakBackend() below raises clearly
                pass
            _backend = EspeakBackend("en-us", preserve_punctuation=False, with_stress=False)
        return _backend


def _phones_to_arabic(phones: str) -> str:
    out: list[str] = []
    i, n = 0, len(phones)
    while i < n:
        if phones[i].isspace():
            i += 1
            continue
        for symbol in _SYMBOLS_LONGEST_FIRST:
            if phones.startswith(symbol, i):
                out.append(_PHONEME_MAP[symbol])
                i += len(symbol)
                break
        else:
            i += 1  # unmapped character (stress/tie marks, stray diacritics) — skip
    return "".join(out)


def transliterate_word(word: str) -> str:
    """Best-effort phonetic Arabic-script rendering of one English word."""
    clean = re.sub(r"[^A-Za-z']", "", word)
    if not clean:
        return word
    backend = _get_backend()
    sep = Separator(phone=" ", word=" | ")
    phones = backend.phonemize([clean], separator=sep, strip=True)[0]
    return "".join(_phones_to_arabic(part) for part in phones.split("|"))


def transliterate_text(text: str) -> str:
    """Transliterate every English word in `text`; punctuation/whitespace
    passes through unchanged so the result reads naturally alongside
    surrounding Arabic."""
    pieces = _WORD_RE.findall(text)
    words = [p for p in pieces if _is_latin_word(p)]
    if not words:
        return text

    backend = _get_backend()
    sep = Separator(phone=" ", word=" | ")
    phoneme_strings = backend.phonemize(words, separator=sep, strip=True)

    out: list[str] = []
    word_iter = iter(phoneme_strings)
    for piece in pieces:
        if _is_latin_word(piece):
            out.append(_phones_to_arabic(next(word_iter)))
        else:
            out.append(piece)
    return "".join(out)
