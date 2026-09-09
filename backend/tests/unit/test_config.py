"""Unit tests for Settings — currently just the CORS origins parsing (the
split-service deployment's one piece of behavior that has real logic to
get wrong: comma-splitting, stray whitespace, blank entries)."""

from __future__ import annotations

from backend.app.config import Settings


def test_cors_allowed_origins_list_is_empty_by_default():
    assert Settings(cors_allowed_origins="").cors_allowed_origins_list == []


def test_cors_allowed_origins_list_splits_on_comma():
    settings = Settings(cors_allowed_origins="https://a.example,https://b.example")
    assert settings.cors_allowed_origins_list == ["https://a.example", "https://b.example"]


def test_cors_allowed_origins_list_strips_whitespace_and_drops_blanks():
    settings = Settings(cors_allowed_origins=" https://a.example ,, https://b.example ")
    assert settings.cors_allowed_origins_list == ["https://a.example", "https://b.example"]
