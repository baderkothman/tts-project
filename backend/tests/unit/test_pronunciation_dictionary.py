"""Pronunciation dictionary lookup tests (FR-052, T127)."""

from __future__ import annotations

from backend.app.data.pronunciation_dictionary import lookup


def test_exact_token_lookup():
    entry = lookup("بيروت")
    assert entry is not None
    assert entry.diacritized == "بَيْرُوت"


def test_alias_lookup():
    entry = lookup("Beirut")
    assert entry is not None
    assert entry.token == "بيروت"


def test_unknown_token_returns_none():
    assert lookup("not-a-real-token-xyz") is None


def test_dialect_scoped_entry_wins_over_unscoped_for_same_token():
    # "meeting" only has a lebanese-scoped entry; requesting a different
    # dialect should not spuriously match it (per lookup's scoping rule).
    assert lookup("meeting", dialect="lebanese") is not None
    assert lookup("meeting", dialect="egyptian") is None
    assert lookup("meeting", dialect=None) is None
