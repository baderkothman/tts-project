"""Missing credentials -> reported unavailable, never an exception (FR-024)."""

from backend.app.config import Settings
from backend.app.models.voice import ProviderStatus
from backend.app.providers.azure import AzureProvider
from backend.app.providers.elevenlabs import ElevenLabsProvider


def test_azure_missing_credentials_reports_status_not_exception():
    settings = Settings(azure_speech_key=None, azure_speech_region=None)
    provider = AzureProvider(settings=settings)
    assert provider.available() == ProviderStatus.MISSING_CREDENTIALS
    assert "AZURE_SPEECH_KEY" in provider.unavailable_reason()


def test_elevenlabs_missing_credentials_reports_status_not_exception():
    settings = Settings(elevenlabs_api_key=None)
    provider = ElevenLabsProvider(settings=settings)
    assert provider.available() == ProviderStatus.MISSING_CREDENTIALS
    assert "ELEVENLABS_API_KEY" in provider.unavailable_reason()


def test_azure_with_credentials_reports_available():
    settings = Settings(azure_speech_key="fake-key", azure_speech_region="eastus")
    provider = AzureProvider(settings=settings)
    assert provider.available() == ProviderStatus.AVAILABLE
