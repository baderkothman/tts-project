"""Model registry gate tests (FR-058, T123)."""

from __future__ import annotations

from backend.app.data.hf_model_registry import HF_MODEL_REGISTRY, enabled_for_task, get


def test_no_enabled_entry_has_unverified_license():
    for entry in HF_MODEL_REGISTRY:
        if entry.enabled:
            assert entry.license is not None, (
                f"{entry.id} is enabled with an unverified license — FR-058 forbids this"
            )


def test_get_unknown_id_returns_none_not_raise():
    assert get("does-not-exist") is None


def test_get_known_id():
    entry = get("egyptian-tts-chatterbox")
    assert entry is not None
    assert entry.repo_id == "oddadmix/chatterbox-egyptian-v0"


def test_enabled_for_task_excludes_disabled_entries():
    dialect_tts = enabled_for_task("dialect_tts")
    ids = {e.id for e in dialect_tts}
    assert "egyptian-tts-chatterbox" in ids
    assert "lahgtna-omnivoice-v2" not in ids  # disabled: unverified license/claim
    assert "mms-tts-ara-msa" not in ids  # disabled: non-commercial license


def test_every_entry_has_a_source_url():
    for entry in HF_MODEL_REGISTRY:
        assert entry.source_url.startswith("https://"), entry.id
