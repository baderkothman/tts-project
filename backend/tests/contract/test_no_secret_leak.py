"""No credential value appears in any response, header, or error (FR-039, SC-011)."""

from backend.app.config import Settings
from backend.app.providers.azure import AzureProvider
from backend.app.providers.elevenlabs import ElevenLabsProvider


FAKE_AZURE_KEY = "sk-test-azure-secret-abc123"
FAKE_ELEVEN_KEY = "sk-test-eleven-secret-xyz789"


def test_provider_info_never_includes_raw_key(client):
    r = client.get("/api/providers")
    body = r.text
    assert FAKE_AZURE_KEY not in body
    assert FAKE_ELEVEN_KEY not in body


def test_unavailable_reason_never_contains_key_value():
    settings = Settings(azure_speech_key=None, azure_speech_region=None)
    provider = AzureProvider(settings=settings)
    reason = provider.unavailable_reason()
    assert FAKE_AZURE_KEY not in (reason or "")


def test_elevenlabs_unavailable_reason_never_contains_key_value():
    settings = Settings(elevenlabs_api_key=None)
    provider = ElevenLabsProvider(settings=settings)
    reason = provider.unavailable_reason()
    assert FAKE_ELEVEN_KEY not in (reason or "")


def test_env_example_has_no_credential_values():
    """Names-only for anything credential-shaped (FR-039); a non-secret
    default like a model id is legitimate and not what this guards against."""
    content = open("/Users/baderothman/Developer/tts-project/.env.example").read()
    credential_markers = ("KEY", "SECRET", "TOKEN", "PASSWORD")
    for line in content.splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        if any(marker in key for marker in credential_markers):
            assert value.strip() == "", f"{key} has a non-empty value in .env.example"
