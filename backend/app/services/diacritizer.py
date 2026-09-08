"""Arabic automatic diacritization (تشكيل) — `basharalrfooh/Fine-Tashkeel`,
a ByT5 fine-tuned on the Tashkeela corpus (published DER 0.95%, WER 2.49%
per its model card; MIT license). Chosen over building diacritization rules
by hand, and over heavier/less-documented alternatives found during
research (CATT needs a manual GitHub-release checkpoint download rather
than a clean `transformers`/HF Hub load; a causal-LM instruction-tuned
option like Tashkeel-350M-v2 risks paraphrasing rather than only inserting
marks) — this one is a plain `AutoModelForSeq2SeqLM`, loads and runs with
no custom package, and ships a benchmark number to cite instead of a bare
claim. Full candidate comparison: `docs/DIACRITIZATION_EVALUATION.md`.

Two policies below exist because of real, reproduced model behavior, not
speculation:

1. **Never re-diacritize text that already carries any diacritic.** Feeding
   the model already-vocalized input (e.g. "اَلسَّلَامُ عَلَيْكُمْ") was tested
   directly during this feature's development and produces corrupted,
   doubled-up marks ("اَلسََّّلِيَامُُ..." — stacked shaddas/dammas, not a
   minor artifact). The task's "preserve user diacritics" requirement turns
   out to be a correctness requirement, not just a politeness one — see
   the reproduction note above `_HAS_DIACRITIC_RE`.
2. **Strip word-final case-ending (i'rab) marks for any non-MSA dialect.**
   Also tested directly: on real Levantine/Gulf input, the model
   consistently appends full MSA grammatical-case endings to dialectal
   words that don't carry them in speech — e.g. "روح" (colloquial "go") came
   back as "رُوحٍ" (a genitive-case noun reading, "spirit/soul[gen]"), and
   "بدي" ("I want") came back "بَدِيُّ" with a spurious doubled ending. Both
   are real, observed mispronunciation risks, not a hypothetical concern
   (Constitution V). Internal (stem) vowels are usually still correct and
   are kept; only the last diacritic on each word is dropped when
   `dialect_id != "msa"`, letting Lahgtna's own dialect-language
   conditioning (not a case ending literally not spoken in dialect) carry
   the word's actual pronunciation.
"""

from __future__ import annotations

import logging
import re
import threading
from functools import lru_cache

logger = logging.getLogger("lahgtna.diacritizer")

_MODEL_NAME = "basharalrfooh/Fine-Tashkeel"

# U+064B..U+0652: the eight tashkeel marks (fatha/damma/kasra/sukun/shadda/
# the three tanween forms) + U+0670 (dagger alif, a vowel mark in its own
# right). Presence of any of these means "treat this text as already
# prepared" (see module docstring, point 1).
_DIACRITIC_CHARS = "ًٌٍَُِّْٰ"
_HAS_DIACRITIC_RE = re.compile(f"[{_DIACRITIC_CHARS}]")

# Only short vowels + tanween — deliberately excludes sukun (ْ, "no vowel
# here", harmless either way) and shadda (ّ, real consonant gemination, not
# a grammatical case ending; stripping it would delete actual pronounced
# content, e.g. dialectal "عمّ" ('amma) losing its doubled م). Point 2 of
# the module docstring only concerns the case-ending vowel/tanween itself.
_TRAILING_VOWEL_RE = re.compile("[ًٌٍَُِ]+$")

_lock = threading.Lock()
_model = None
_tokenizer = None
_load_error: str | None = None


def has_diacritics(text: str) -> bool:
    return bool(_HAS_DIACRITIC_RE.search(text))


def load() -> None:
    """Load the model once, eagerly (e.g. from `main.py`'s startup). Safe to
    call even though `diacritize()` would lazy-load it anyway on first use —
    calling it explicitly at startup means the first real request doesn't
    pay that cost."""
    _load()


def _load() -> None:
    global _model, _tokenizer, _load_error
    with _lock:
        if _model is not None:
            return
        if _load_error is not None:
            # Already tried and failed once (e.g. disk full, network down) —
            # real production case: retrying the same failing multi-hundred-MB
            # download on every single /api/tts request (diacritize() lazy-
            # loads too) turned one bad deploy into every request paying a
            # slow, doomed retry. Fail fast instead.
            raise RuntimeError(_load_error)
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        logger.info("Loading diacritizer %s (this runs once)", _MODEL_NAME)
        try:
            _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
            _model = AutoModelForSeq2SeqLM.from_pretrained(_MODEL_NAME)
            _model.eval()
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            logger.exception("Diacritizer failed to load")
            raise


def is_loaded() -> bool:
    return _model is not None


def load_error() -> str | None:
    return _load_error


def _strip_word_final_irab(text: str) -> str:
    """Drop only the last diacritic run of each whitespace-delimited word —
    the grammatical case ending — leaving internal (stem) vowels intact."""
    words = text.split(" ")
    return " ".join(_TRAILING_VOWEL_RE.sub("", w) for w in words)


def _max_new_tokens(input_len: int) -> int:
    """Diacritized output is always *longer* than its input in ByT5's
    byte-level tokens — every letter can gain a combining mark (2 more
    UTF-8 bytes each). A fixed generation cap silently truncates long
    input: `generate()` just stops at the limit with no error, no
    truncation marker, and `_tokenizer.decode` happily returns whatever
    partial output it got — which reads as text (often whole trailing
    lines) having vanished. Scale the cap to the actual input instead of
    trusting one constant to cover every input length; capped so a
    pathological single line can't run away."""
    return min(2048, max(512, input_len * 3))


@lru_cache(maxsize=512)
def _run_model(text: str) -> str:
    import torch

    _load()
    input_ids = _tokenizer(text, return_tensors="pt").input_ids
    with torch.inference_mode():
        output_ids = _model.generate(
            input_ids, max_new_tokens=_max_new_tokens(input_ids.shape[-1])
        )
    return _tokenizer.decode(output_ids[0], skip_special_tokens=True)


def diacritize(text: str, *, dialect_id: str = "msa") -> tuple[str, bool]:
    """Returns `(result, model_was_applied)`.

    `model_was_applied` is False when the input already had diacritics (so
    it was passed through untouched — see module docstring) or when the
    segment is empty/whitespace.

    Processed line-by-line rather than as one blob: `text_preprocessor.py`
    segments by *language*, not by line, so a multi-line Arabic block
    (e.g. several lines pasted into the textarea) arrives here as a single
    string with embedded newlines. Feeding that whole thing through one
    `_run_model()` call put every line's fate behind a single generation
    budget — real reproduced bug: a long paste got diacritized correctly up
    to the token cap and everything after that point (often entire trailing
    lines) came back missing, with nothing to indicate truncation had
    happened. Splitting on "\\n" first means one line's generation can
    never eat into another line's budget.
    """
    if not text.strip():
        return text, False

    lines = text.split("\n")
    results = []
    applied = False
    for line in lines:
        line_result, line_applied = _diacritize_line(line, dialect_id)
        results.append(line_result)
        applied = applied or line_applied
    return "\n".join(results), applied


def _diacritize_line(text: str, dialect_id: str) -> tuple[str, bool]:
    if not text.strip():
        return text, False
    if has_diacritics(text):
        return text, False

    # The tokenize -> generate -> decode round trip silently drops leading/
    # trailing whitespace (observed directly: a segment like " مع الـ "
    # came back "مَع الـ", losing the word-boundary space against whatever
    # sits before it once segments are rejoined) — stripped here and
    # reattached after, rather than trusting the model to preserve it.
    leading_ws = text[: len(text) - len(text.lstrip())]
    trailing_ws = text[len(text.rstrip()) :]
    core = text.strip()

    try:
        result = _run_model(core)
    except Exception:  # noqa: BLE001
        # main.py's startup lifespan already promises a failed diacritizer
        # "degrades gracefully (diacritization is skipped)" instead of
        # blocking the app — real reproduced bug: that promise only held at
        # startup. A request-time retry (this call, via `_load()` inside
        # `_run_model`) propagated the load failure straight into a 500 for
        # every /api/tts call instead. `_load()`'s own logger.exception
        # already recorded the real cause; degrade here too, once per call,
        # rather than failing the whole request over a non-essential step.
        return text, False
    if dialect_id != "msa":
        result = _strip_word_final_irab(result)
    result = leading_ws + result + trailing_ws
    return result, True
