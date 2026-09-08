"""Custom pronunciation overrides — names/brands/acronyms whose default
handling (Kokoro English TTS, or the phonetic-transliteration fallback)
comes out wrong, corrected once and reused everywhere.

Overrides live in `backend/app/data/pronunciation_overrides.json` as
`{"term": "Arabic-script phonetic rendering"}`. Applying an override
rewrites the term to its Arabic-script form *before* language segmentation
runs, so the term is spoken by the Arabic TTS engine directly — no
dedicated UI is needed to add one; editing the JSON file is enough (task
requirement: "should not initially require a complex UI").

Deliberately data, not code: the architecture supports arbitrarily many
overrides without touching `text_preprocessor.py` or any pipeline logic.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "pronunciation_overrides.json"

_lock = threading.Lock()
_cache: dict[str, str] | None = None
_compiled: re.Pattern[str] | None = None
_loaded_path: Path | None = None


def _load(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object of term -> pronunciation")
    return {str(k): str(v) for k, v in data.items()}


def _get_overrides(path: Path) -> tuple[dict[str, str], re.Pattern[str] | None]:
    global _cache, _compiled, _loaded_path
    with _lock:
        if _cache is not None and _loaded_path == path:
            return _cache, _compiled
        overrides = _load(path)
        if overrides:
            # Longest term first so "development team" (if ever added) would
            # win over a standalone "development" entry; \b boundaries keep
            # this to whole-word/whole-phrase matches in Latin script.
            terms = sorted(overrides.keys(), key=len, reverse=True)
            pattern = re.compile(
                r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b",
                re.IGNORECASE,
            )
        else:
            pattern = None
        _cache, _compiled, _loaded_path = overrides, pattern, path
        return overrides, pattern


def apply_overrides(text: str, *, path: Path = _DEFAULT_PATH) -> str:
    """Replace every occurrence of a known term with its Arabic-script
    pronunciation. Matching is case-insensitive on the Latin term but the
    replacement is used verbatim (its own casing is irrelevant — it's
    Arabic script)."""
    overrides, pattern = _get_overrides(path)
    if not pattern:
        return text

    # Build a case-insensitive lookup once per call (overrides dict itself
    # stays case-sensitive-keyed, e.g. distinguishing "UI" from a
    # hypothetical "ui").
    lower_lookup = {k.lower(): v for k, v in overrides.items()}

    def _replace(match: re.Match[str]) -> str:
        term = match.group(0)
        return overrides.get(term) or lower_lookup.get(term.lower(), term)

    return pattern.sub(_replace, text)


def reload_overrides(path: Path = _DEFAULT_PATH) -> None:
    """Drop the cache — picks up edits to the JSON file without a restart."""
    global _cache, _compiled, _loaded_path
    with _lock:
        _cache, _compiled, _loaded_path = None, None, None
