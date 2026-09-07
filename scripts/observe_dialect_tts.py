"""Generate audio for the Egyptian dialect sample sentences through every
architecture available for that dialect, and record which ones actually ran
(FR-054, FR-061, tasks.md T144-T145).

Run manually: .venv/bin/python scripts/observe_dialect_tts.py

IMPORTANT HONESTY NOTE (Constitution V): this script makes REAL calls — the
Edge baseline needs no credentials and always runs; the Hugging Face
candidate (`oddadmix/chatterbox-egyptian-v0`) requires HF_TOKEN and is
SKIPPED, not faked, when it is absent. No listening-based dialect-accuracy
score is recorded for a rendering this script did not actually produce.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.config import get_settings
from backend.app.data.hf_model_registry import get as get_hf_model
from backend.app.providers.base import ProviderError, ProviderRequest
from backend.app.providers.edge import EdgeProvider
from backend.app.providers.huggingface.provider import HuggingFaceProvider
from backend.app.services.voice_router import resolve_voice

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "audio" / "dialect"

# From spec.md's dialect conversational sample sets (Story 6).
EGYPTIAN_SAMPLES = [
    ("egy-1", "إزيك؟ عامل إيه؟"),
    ("egy-2", "أنا لسه في الطريق وهكون عندك كمان عشر دقايق."),
    ("egy-3", "بص، خلينا نجرب الموضوع الأول وبعد كده نقرر."),
]

LEBANESE_SAMPLES = [
    ("leb-1", "كيفك؟ شو الأخبار؟ اليوم الجو كتير حلو."),
    ("leb-2", "شو رأيك نطلع نشرب قهوة بعد الشغل؟"),
    ("leb-3", "أنا بعدني بالطريق، بوصل عندك بعد شي عشر دقايق."),
    ("leb-4", "ما بعرف إذا رح نلحق، بس خلينا نجرب."),
    ("leb-5", "بكرا عندي meeting عالـ 10، وبعدها بدنا نعمل deploy للـ API."),
]

GULF_SAMPLES = [
    ("gulf-1", "وش رايك نطلع اليوم؟"),
    ("gulf-2", "إن شاء الله الأمور تمام."),
    ("gulf-3", "ترى الاجتماع الساعة ثلاث، لا تتأخر."),
    ("gulf-4", "أبشر، بخليك تعرف أول ما أوصل."),
]


async def _run_edge_locale(locale: str, samples: list[tuple[str, str]], tag: str) -> list[str]:
    provider = EdgeProvider()
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale=locale)
    produced = []
    for label, text in samples:
        request = ProviderRequest(text=text, voice=voice)
        chunks = [c async for c in provider.stream(request)]
        audio = b"".join(chunks)
        path = OUT_DIR / f"{label}-{tag}.mp3"
        path.write_bytes(audio)
        produced.append(str(path))
    return produced


async def _run_groq(samples: list[tuple[str, str]], settings) -> tuple[list[str], str | None]:
    if not settings.has_groq():
        return [], "GROQ_API_KEY not configured"
    try:
        from backend.app.providers.groq import GroqProvider
    except ImportError as exc:
        return [], f"Groq adapter unavailable: {exc}"

    provider = GroqProvider(settings=settings)
    voices = await provider.get_voices()
    voice = resolve_voice(provider, voices, locale="ar-SA")
    produced = []
    for label, text in samples:
        request = ProviderRequest(text=text, voice=voice)
        try:
            chunks = [c async for c in provider.stream(request)]
        except ProviderError as exc:
            return produced, f"Groq call failed on {label}: [{exc.kind}] {exc.message}"
        audio = b"".join(chunks)
        path = OUT_DIR / f"{label}-groq.mp3"
        path.write_bytes(audio)
        produced.append(str(path))
    return produced, None


async def _run_huggingface(settings) -> tuple[list[str], str | None]:
    model = get_hf_model("egyptian-tts-chatterbox")
    if model is None or not model.enabled:
        return [], "egyptian-tts-chatterbox is not enabled in the registry"
    if not settings.has_huggingface():
        return [], "HF_TOKEN not configured — cannot call the hosted Inference API"

    provider = HuggingFaceProvider(settings=settings)
    voices = await provider.get_voices()
    target = next((v for v in voices if v.provider_voice_id == model.repo_id), None)
    if target is None:
        return [], f"{model.repo_id} did not resolve to a voice (see provider.get_voices())"

    produced = []
    for label, text in EGYPTIAN_SAMPLES:
        request = ProviderRequest(text=text, voice=target)
        try:
            audio = await provider.synthesize(request)
        except ProviderError as exc:
            return produced, f"{model.repo_id} call failed: [{exc.kind}] {exc.message}"
        path = OUT_DIR / f"{label}-hf-chatterbox.mp3"
        path.write_bytes(audio)
        produced.append(str(path))
    return produced, None


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()

    print("== Egyptian: existing TTS (Edge, ar-EG) ==")
    for f in await _run_edge_locale("ar-EG", EGYPTIAN_SAMPLES, "edge"):
        print(f"  wrote {f}")

    print("\n== Egyptian: Hugging Face dialect-specific TTS (oddadmix/chatterbox-egyptian-v0) ==")
    hf_files, hf_reason = await _run_huggingface(settings)
    if hf_files:
        for f in hf_files:
            print(f"  wrote {f}")
    else:
        print(f"  SKIPPED — {hf_reason}")
        print(
            "  No dialect-accuracy claim is recorded for this candidate until "
            "it is actually run and listened to (Constitution V)."
        )

    print("\n== Lebanese/Levantine: existing TTS (Edge, ar-LB) ==")
    for f in await _run_edge_locale("ar-LB", LEBANESE_SAMPLES, "edge"):
        print(f"  wrote {f}")
    print("  (No dialect-specific HF TTS candidate cleared research.md R11 for Lebanese/Levantine yet.)")

    print("\n== Saudi/Gulf: existing TTS — Edge ar-SA (MSA-trained) baseline ==")
    for f in await _run_edge_locale("ar-SA", GULF_SAMPLES, "edge"):
        print(f"  wrote {f}")

    print("\n== Saudi/Gulf: existing TTS — Groq Orpheus Arabic (genuinely dialect-trained) ==")
    groq_files, groq_reason = await _run_groq(GULF_SAMPLES, settings)
    if groq_files:
        for f in groq_files:
            print(f"  wrote {f}")
    else:
        print(f"  SKIPPED — {groq_reason}")
    print("  (No dialect-specific HF TTS candidate cleared research.md R11 for Saudi/Gulf yet.)")

    print("\nNext: listen to each set and record scores in docs/DIALECT_EVALUATION.md")
    print("(naturalness, pronunciation, dialect accuracy, prosody, English-mixing, voice quality — /5 each).")


if __name__ == "__main__":
    asyncio.run(main())
