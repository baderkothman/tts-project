"""SSML-like user text is escaped, never interpreted (FR-041, AC-05, SC-012)."""

from backend.app.text_processing.provider_formatting import build_ssml
from backend.app.data.voices import EDGE_VOICES


def test_markup_tags_are_escaped():
    malicious = "</speak><script>alert(1)</script>"
    ssml = build_ssml(malicious, EDGE_VOICES[0])
    assert "<script>" not in ssml
    assert "&lt;script&gt;" in ssml


def test_ssml_structure_stays_well_formed():
    malicious = '"><voice name="evil">'
    ssml = build_ssml(malicious, EDGE_VOICES[0])
    # Exactly one real <voice> element should exist — the one we constructed.
    assert ssml.count("<voice name=") == 1


def test_ampersand_escaped():
    ssml = build_ssml("Q&A نقاش", EDGE_VOICES[0])
    assert "&amp;" in ssml
    assert " & " not in ssml
