"""DialectProfile data tests (FR-049, FR-050, T125)."""

from __future__ import annotations

from backend.app.data.dialect_profiles import DIALECT_PROFILES, get
from backend.app.models.voice import Dialect

_REQUIRED_IDS = {"msa", "levantine", "lebanese", "gulf", "saudi", "egyptian"}


def test_all_six_minimum_profiles_present():
    ids = {p.id for p in DIALECT_PROFILES}
    assert _REQUIRED_IDS <= ids


def test_every_profile_family_is_a_valid_dialect_enum_value():
    for profile in DIALECT_PROFILES:
        assert isinstance(profile.dialect_family, Dialect)


def test_get_unknown_returns_none():
    assert get("klingon") is None


def test_lebanese_is_narrower_than_levantine_family():
    lebanese = get("lebanese")
    levantine = get("levantine")
    assert lebanese.dialect_family == Dialect.LEVANTINE == levantine.dialect_family
    assert lebanese.locale == "ar-LB"
    assert levantine.locale is None  # spans multiple locales, none singularly represents it


def test_no_normalization_rule_claims_to_flatten_toward_msa():
    # FR-050: dialect vocabulary must never be rewritten toward MSA. No rule
    # references currently exist (honest absence), so this simply guards
    # against a future rule being added with an MSA-flattening name.
    for profile in DIALECT_PROFILES:
        for rule_ref in profile.normalization_rules:
            assert "msa" not in rule_ref.lower() or "preserve" in rule_ref.lower()


def test_every_profile_has_at_least_one_fallback_voice():
    for profile in DIALECT_PROFILES:
        assert profile.fallback_tts_models, f"{profile.id} has no fallback (FR-057 needs one)"
