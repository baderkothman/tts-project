"""Generate before/after pronunciation audio for candidate defect cases.

Run manually: .venv/bin/python scripts/observe_pronunciation.py

IMPORTANT HONESTY NOTE (Constitution V): this script produces REAL audio from
the live Edge provider for each candidate — it does not fabricate output. But
no ASR or audio-transcription tool was available in the implementation
environment (an openai-whisper install was attempted and abandoned as too
heavy for the sandbox; no cloud ASR credentials were configured), so the
mispronunciation itself could not be perceptually confirmed by this script or
its author. The demo case below is chosen because the underlying ambiguity is
a well-documented fact of Arabic orthography (undiacritized homographs), not
an invented scenario — but the generated audio pair is offered for a human
listener to confirm, and docs/PRONUNCIATION.md states this limitation
explicitly rather than claiming a perceptual verification that did not happen.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.data.voices import EDGE_VOICES
from backend.app.providers.base import ProviderRequest
from backend.app.providers.edge import EdgeProvider
from backend.app.services.voice_router import resolve_voice

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "audio"

# Candidate cases: (label, raw_text, corrected_text, note)
CANDIDATES = [
    (
        "ilm-ambiguous",
        "طلب العلم فريضة على كل مسلم ومسلمة",
        "طلب العِلْم فريضة على كل مسلم ومسلمة",
        "'العلم' undiacritized is ambiguous between 'ilm' (knowledge), "
        "'alam' (flag), and the verb 'alima' (he knew); the diacritized "
        "form forces the knowledge reading.",
    ),
    (
        "chatgpt-brand",
        "أنا أستخدم ChatGPT كل يوم في عملي",
        "أنا أستخدم تشات جي بي تي كل يوم في عملي",
        "Latin brand name left unrendered/mangled by an Arabic-voice engine "
        "vs. an Arabic phonetic respelling.",
    ),
]


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale="ar-SA")

    for label, raw, corrected, note in CANDIDATES:
        for variant, text in (("before", raw), ("after", corrected)):
            request = ProviderRequest(text=text, voice=voice)
            chunks = [c async for c in provider.stream(request)]
            audio = b"".join(chunks)
            out_path = OUT_DIR / f"{label}-{variant}.mp3"
            out_path.write_bytes(audio)
            print(f"{label}/{variant}: {len(audio)} bytes -> {out_path}")
        print(f"  note: {note}")
        print(f"  voice: {voice.provider_voice_id} (provider={provider.id})")
        print()


if __name__ == "__main__":
    asyncio.run(main())
