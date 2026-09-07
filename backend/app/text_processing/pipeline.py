"""The text processing pipeline (FR-015, FR-016).

Stage order is fixed and significant: dates and currencies MUST run before the
generic numbers stage, because the numbers stage's digit patterns are greedy
and would otherwise consume "27/09/2026" or "1,250.50" as plain numerals before
the date/currency patterns ever see them intact. This was caught by running
the pipeline end-to-end during implementation, not assumed (Constitution V).
Pronunciation rules run last so they can override any earlier stage's output.
Every stage is a pure `str -> str` function (Constitution VIII), so each is
independently testable without network access.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from backend.app.models.tts import ProcessedText, StageDiff
from backend.app.text_processing.abbreviations import verbalize_abbreviations
from backend.app.text_processing.arabic_normalizer import normalize
from backend.app.text_processing.code_switching import handle_code_switching
from backend.app.text_processing.currencies import verbalize_currencies
from backend.app.text_processing.dates import verbalize_dates
from backend.app.text_processing.numbers import verbalize_numbers
from backend.app.text_processing.pronunciation import apply_pronunciation_rules

# Fixed order. Do not reorder without re-reading the rationale above.
_STAGES: list[tuple[str, Callable[[str], str]]] = [
    ("normalize", normalize),
    ("dates", verbalize_dates),
    ("currencies", verbalize_currencies),
    ("numbers", verbalize_numbers),
    ("abbreviations", verbalize_abbreviations),
    ("code_switching", handle_code_switching),
]


def process_text(
    text: str,
    *,
    apply_preprocessing: bool = True,
    apply_pronunciation: bool = True,
    locale: str | None = None,
    provider: str | None = None,
) -> ProcessedText:
    """Run the full pipeline, recording a diff for every stage that ran.

    `apply_preprocessing` and `apply_pronunciation` are independent switches so
    the before/after pronunciation demo can hold everything else constant
    (FR-020).
    """
    original = text
    current = text
    diffs: list[StageDiff] = []

    stages = list(_STAGES) if apply_preprocessing else []
    if apply_pronunciation:
        stages.append(
            (
                "pronunciation",
                lambda t: apply_pronunciation_rules(t, locale=locale, provider=provider),
            )
        )

    for name, fn in stages:
        before = current
        t0 = perf_counter()
        after = fn(before)
        duration_ms = (perf_counter() - t0) * 1000.0
        diffs.append(
            StageDiff(
                stage_name=name,
                before=before,
                after=after,
                changed=before != after,
                duration_ms=duration_ms,
            )
        )
        current = after

    return ProcessedText(
        original=original,
        processed=current,
        stages=diffs,
        changed=current != original,
    )
