"""Microsoft Edge Neural TTS adapter — the credential-free primary provider
(research R1).

Verified locally before implementation: 32 Arabic voices across 16 locales,
genuine chunked streaming (41 chunks, cold TTFA ~2.5s). This is what makes the
prototype runnable, benchmarkable, and its pronunciation demo *observable*
(Constitution V) in an environment with no paid credentials.

The `edge-tts` client accepts exactly rate/volume/pitch — no SSML, no style,
no phoneme (verified by inspecting its `Communicate.__init__` signature) — and
escapes its own input, so this adapter cannot express native styles and cannot
be subject to markup injection regardless of what text it receives.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import edge_tts

from backend.app.data.voices import EDGE_VOICES
from backend.app.models.voice import AudioFormat, Capabilities, ProviderStatus, VoiceConfig
from backend.app.providers.base import ProviderError, ProviderRequest, TTSProvider
from backend.app.text_processing.provider_formatting import prosody_for_style


def _fmt_percent(value: float) -> str:
    """edge-tts requires rate/volume as an integer percent: r'^[+-]\\d+%$'
    (verified against edge_tts.data_classes.TTSConfig's own validation)."""
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(round(value))}%"


def _fmt_hz(value: float) -> str:
    """edge-tts requires pitch as an integer Hz offset: r'^[+-]\\d+Hz$'.
    Our style table expresses pitch as a percent-ish shift; a fixed
    percent-to-Hz scale (against a ~200Hz baseline pitch) converts it. This is
    an approximation, consistent with prosody-mapped style being reported as
    non-native (emotion_native=False, research R3)."""
    hz = value * 2.0  # 1% ~= 2Hz against a ~200Hz baseline
    sign = "+" if hz >= 0 else "-"
    return f"{sign}{abs(round(hz))}Hz"


class EdgeProvider(TTSProvider):
    id = "edge"
    display_name = "Microsoft Edge Neural TTS"

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            ssml=False,
            phoneme=False,
            # Verified: no Microsoft Arabic voice exposes speaking styles or
            # roles (research R2). Emotion is prosody-approximated only.
            native_emotions=False,
            prosody_rate=True,
            prosody_pitch=True,
            prosody_volume=True,
            locales=sorted({v.locale for v in EDGE_VOICES}),
            formats=[AudioFormat.MP3_24KHZ],
            max_chars=5000,
            requires_credentials=False,
            notes="Unofficial Microsoft Edge read-aloud endpoint. No SLA. "
            "Suitable for prototyping; Azure AI Speech is the production path "
            "for the same voice family.",
        )

    def available(self) -> ProviderStatus:
        # No credentials required; readiness is not checked with network I/O
        # here (PC-02) — a transient network failure surfaces per-request as
        # a retryable ProviderError instead.
        return ProviderStatus.AVAILABLE

    async def get_voices(self) -> list[VoiceConfig]:
        return list(EDGE_VOICES)

    def _prosody(self, request: ProviderRequest) -> tuple[str, str, str]:
        rate_pct, pitch_pct, vol_pct = prosody_for_style(request.emotion)
        # Explicit rate/pitch overrides in the request take precedence over
        # the style-derived defaults.
        if request.speaking_rate is not None:
            rate_pct = request.speaking_rate * 100 - 100
        if request.pitch is not None:
            pitch_pct = request.pitch
        return _fmt_percent(rate_pct), _fmt_hz(pitch_pct), _fmt_percent(vol_pct)

    async def stream(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        rate, pitch, volume = self._prosody(request)
        # FR-032/PC-07: every provider call carries an explicit timeout.
        # edge-tts splits this into a connect phase and a receive phase; we
        # derive both from the single request-level budget.
        timeout_s = max(1, int(request.timeout_s))
        communicate = edge_tts.Communicate(
            text=request.text,
            voice=request.voice.provider_voice_id,
            rate=rate,
            pitch=pitch,
            volume=volume,
            connect_timeout=min(10, timeout_s),
            receive_timeout=timeout_s,
        )
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except edge_tts.exceptions.NoAudioReceived as exc:
            raise ProviderError(self.id, "server", str(exc)) from exc
        except TimeoutError as exc:
            raise ProviderError(self.id, "timeout", str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - single translation boundary (PC-06)
            raise ProviderError(self.id, "server", str(exc)) from exc

    async def synthesize(self, request: ProviderRequest) -> bytes:
        chunks = [c async for c in self.stream(request)]
        return b"".join(chunks)
