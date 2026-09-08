"""Data-integrity tests for the dialect catalogue (data/dialects.py).

These pin down the facts established by directly reading the installed
`omnivoice` package's `lang_map.py` (see that module's docstring for the
sourcing) — a regression here means the catalogue drifted from what the
model actually accepts.
"""

from __future__ import annotations

from backend.app.data.dialects import (
    DIALECTS,
    PLANNED_NOT_IMPLEMENTED,
    REMOVED_UNRELIABLE_DIALECTS,
)

# Snapshot of the installed omnivoice package's actual Arabic-relevant
# LANG_NAME_TO_ID entries at the time this catalogue was written. `apc`
# (Levantine) is no longer used by anything exposed here — see
# REMOVED_UNRELIABLE_DIALECTS — but is left in this whitelist since it's
# still a real, valid code in the installed package.
_KNOWN_VALID_CODES = {"arz", "ars", "ary", "acm", "apd", "apc", "ayl", "aeb", "abv", "arq", "arb"}


def test_nine_reliable_dialects_plus_msa():
    # Lahgtna's own model card marks 13 dialects "completed", but 4
    # (Palestinian/Lebanese/Syrian/Yemeni) were removed after real user
    # feedback that they don't work — see data/dialects.py's module
    # docstring and REMOVED_UNRELIABLE_DIALECTS. MSA is this app's own
    # addition as the always-available baseline.
    assert len(DIALECTS) == 10


def test_every_dialect_id_is_unique():
    ids = [d.id for d in DIALECTS]
    assert len(ids) == len(set(ids))


def test_language_codes_are_either_none_or_verified_real():
    for d in DIALECTS:
        if d.language_code is not None:
            assert d.language_code in _KNOWN_VALID_CODES, (
                f"{d.id} uses an unverified language code {d.language_code!r}"
            )


def test_no_currently_exposed_dialect_is_written_only():
    # The mechanism still exists in the Dialect model for any future
    # dialect that ends up sharing/lacking a code the way the 4 removed
    # ones did, but nothing currently shipped needs it: every exposed
    # dialect has its own distinct, verified language code.
    assert all(not d.written_only for d in DIALECTS)
    assert all(d.language_code is not None for d in DIALECTS)


def test_planned_dialects_are_documented_but_never_selectable():
    assert "United Arab Emirates" in PLANNED_NOT_IMPLEMENTED
    implemented_names = {d.name_en.lower() for d in DIALECTS}
    for planned in PLANNED_NOT_IMPLEMENTED:
        assert planned.lower() not in implemented_names


def test_removed_unreliable_dialects_are_documented_but_never_selectable():
    assert "Palestinian" in REMOVED_UNRELIABLE_DIALECTS
    implemented_names = {d.name_en.lower() for d in DIALECTS}
    for removed in REMOVED_UNRELIABLE_DIALECTS:
        assert removed.lower() not in implemented_names
