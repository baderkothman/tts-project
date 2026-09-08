from __future__ import annotations

import json

import pytest

from backend.app.services import pronunciation_dictionary as pd


@pytest.fixture
def overrides_path(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps({"React": "رياكت", "API": "إيه بي آي"}), encoding="utf-8")
    pd.reload_overrides(path)
    yield path
    pd.reload_overrides(path)


def test_applies_known_term(overrides_path):
    result = pd.apply_overrides("جرب React اليوم", path=overrides_path)
    assert "رياكت" in result
    assert "React" not in result


def test_case_insensitive_match(overrides_path):
    result = pd.apply_overrides("جرب react اليوم", path=overrides_path)
    assert "رياكت" in result


def test_whole_word_only_no_partial_match(overrides_path):
    # "Reactive" must not be corrupted by a "React" substring match.
    result = pd.apply_overrides("Reactive framework", path=overrides_path)
    assert result == "Reactive framework"


def test_unknown_term_untouched(overrides_path):
    assert pd.apply_overrides("جرب Vue اليوم", path=overrides_path) == "جرب Vue اليوم"


def test_missing_file_is_a_no_op(tmp_path):
    pd.reload_overrides(tmp_path / "does_not_exist.json")
    assert pd.apply_overrides("جرب React اليوم", path=tmp_path / "does_not_exist.json") == "جرب React اليوم"


def test_multiple_terms_in_one_sentence(overrides_path):
    result = pd.apply_overrides("React uses an API", path=overrides_path)
    assert "رياكت" in result
    assert "إيه بي آي" in result
