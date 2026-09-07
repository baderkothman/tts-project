"""Missing credentials -> reported unavailable, never an exception (FR-024)."""

from backend.app.config import Settings
from backend.app.models.voice import ProviderStatus
from backend.app.providers.elevenlabs import ElevenLabsProvider
from backend.app.providers.groq import GroqProvider


def test_groq_missing_credentials_reports_status_not_exception():
    settings = Settings(groq_api_key=None)
    provider = GroqProvider(settings=settings)
    assert provider.available() == ProviderStatus.MISSING_CREDENTIALS
    assert "GROQ_API_KEY" in provider.unavailable_reason()


def test_elevenlabs_missing_credentials_reports_status_not_exception():
    settings = Settings(elevenlabs_api_key=None)
    provider = ElevenLabsProvider(settings=settings)
    assert provider.available() == ProviderStatus.MISSING_CREDENTIALS
    assert "ELEVENLABS_API_KEY" in provider.unavailable_reason()


def test_groq_with_credentials_reports_available():
    settings = Settings(groq_api_key="fake-key")
    provider = GroqProvider(settings=settings)
    assert provider.available() == ProviderStatus.AVAILABLE
