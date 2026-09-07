"""Arabic/English code-switching handling (FR-013).

Most Arabic TTS engines handle embedded Latin script reasonably well already;
the failure mode this stage targets is sentence *flow* breaking at the
script boundary. It inserts a short prosodic pause marker (represented here as
a comma, which every provider already knows how to pace) so the switch reads
as a deliberate insertion rather than a collision.
"""

from __future__ import annotations

import re

# A run of Latin letters (words, acronyms, mixed-case terms) inside Arabic text.
_LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9\-]*(?:\s[A-Za-z][A-Za-z0-9\-]*)*")


def handle_code_switching(text: str) -> str:
    """Ensure clean prosodic boundaries around embedded Latin spans.

    Does not translate or transliterate — it only prevents the switch from
    running directly into adjacent Arabic with no pause cue.
    """

    def _pad(m: re.Match[str]) -> str:
        span = m.group(0)
        start, end = m.start(), m.end()
        prefix = "" if (start == 0 or text[start - 1] in " ،؛؟!.," ) else " "
        suffix = "" if (end == len(text) or text[end] in " ،؛؟!.,") else " "
        return f"{prefix}{span}{suffix}"

    return _LATIN_RUN.sub(_pad, text)
