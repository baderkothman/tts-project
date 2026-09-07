"""Data-integrity tests for the dialect catalogue (data/dialects.py).

These pin down the facts established by directly reading the installed
`omnivoice` package's `lang_map.py` (see that module's docstring for the
sourcing) — a regression here means the catalogue drifted from what the
model actually accepts.
"""

from __future__ import annotations

from backend.app.data.dialects import DIALECT_BY_ID, DIALECTS, PLANNED_NOT_IMPLEMENTED

# Snapshot of the installed omnivoice package's actual Arabic-relevant
# LANG_NAME_TO_ID entries at the time this catalogue was written.
_KNOWN_VALID_CODES = {"arz", "ars", "ary", "acm", "apd", "apc", "ayl", "aeb", "abv", "arq", "arb"}


def test_thirteen_completed_dialects_plus_msa():
    # Lahgtna's own model card marks exactly 13 dialects "completed"; MSA is
    # this app's own addition as the always-available baseline.
    assert len(DIALECTS) == 14


def test_every_dialect_id_is_unique():
    ids = [d.id for d in DIALECTS]
    assert len(ids) == len(set(ids))


def test_language_codes_are_either_none_or_verified_real():
    for d in DIALECTS:
        if d.language_code is not None:
            assert d.language_code in _KNOWN_VALID_CODES, (
                f"{d.id} uses an unverified language code {d.language_code!r}"
            )


def test_written_only_dialects_have_no_code_or_a_shared_one():
    # Palestinian/Lebanese/Syrian share Levantine's apc code; Yemeni has none.
    assert DIALECT_BY_ID["yemeni"].language_code is None
    assert DIALECT_BY_ID["yemeni"].written_only is True
    for dialect_id in ("palestinian", "lebanese", "syrian"):
        assert DIALECT_BY_ID[dialect_id].language_code == "apc"
        assert DIALECT_BY_ID[dialect_id].written_only is True


def test_planned_dialects_are_documented_but_never_selectable():
    assert "United Arab Emirates" in PLANNED_NOT_IMPLEMENTED
    implemented_names = {d.name_en.lower() for d in DIALECTS}
    for planned in PLANNED_NOT_IMPLEMENTED:
        assert planned.lower() not in implemented_names
