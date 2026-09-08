#!/usr/bin/env python3
"""Generates and saves real audio for the sample matrix in `samples.py`
against the live backend, and writes `docs/SAMPLE_GALLERY.md` describing
exactly what was generated — every number and audio file in that doc comes
from this script's own output against the real model, not hand-typed.

Usage:
    .venv/bin/uvicorn backend.app.main:app --port 8000 &   # if not already running
    .venv/bin/python scripts/generate_samples.py
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from samples import ALL_SAMPLES, Sample  # noqa: E402

BASE_URL = "http://localhost:8000"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "audio" / "samples"
GALLERY_PATH = Path(__file__).resolve().parents[1] / "docs" / "SAMPLE_GALLERY.md"

CATEGORY_LABELS = {
    "msa": "1. الفصحى (MSA)",
    "dialect": "2. لهجة عامية",
    "difficult_words": "3. أسماء وكلمات صعبة",
    "mixed_content": "4. أرقام وتواريخ وعملات واختصارات وكلمات إنجليزية",
    "style_variant": "5. نفس الجملة بأنماط/نبرات مختلفة",
}


def generate_one(client: httpx.Client, sample: Sample) -> dict:
    data = {
        "text": sample.text,
        "dialect_id": sample.dialect_id,
        "pitch": sample.pitch,
        "whisper": str(sample.whisper).lower(),
    }
    if sample.gender:
        data["gender"] = sample.gender
    resp = client.post(f"{BASE_URL}/api/tts", data=data, timeout=120.0)
    resp.raise_for_status()
    body = resp.json()

    wav_bytes = base64.b64decode(body["audio_base64"])
    out_path = OUT_DIR / f"{sample.id}.wav"
    out_path.write_bytes(wav_bytes)

    return {
        "sample": sample,
        "processed_text": body["processed_text"],
        "warnings": body["warnings"],
        "latency": body["latency"],
        "audio_path": out_path,
    }


def write_gallery(results: list[dict]) -> None:
    lines = [
        "# Sample Gallery — real generated audio",
        "",
        "Every audio file here and every number in this table was produced by "
        "`scripts/generate_samples.py` calling the real running backend "
        "(`oddadmix/lahgtna-omnivoice-v2`, run locally) — nothing hand-typed or "
        "invented. Re-run the script to regenerate after any pipeline change.",
        "",
    ]

    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["sample"].category, []).append(r)

    for category, label in CATEGORY_LABELS.items():
        if category not in by_category:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for r in by_category[category]:
            s: Sample = r["sample"]
            rel_path = r["audio_path"].relative_to(GALLERY_PATH.parent)
            lines.append(f"### {s.label_ar} (`{s.id}`)")
            lines.append("")
            lines.append(f"- **النص المُدخل:** {s.text}")
            if r["processed_text"] != s.text:
                lines.append(f"- **النص بعد المعالجة (تشكيل + تطبيع):** {r['processed_text']}")
            style = f"- **اللهجة:** `{s.dialect_id}` — النبرة: `{s.pitch}`"
            if s.whisper:
                style += " — همس"
            lines.append(style)
            lat = r["latency"]
            lines.append(
                f"- **زمن التوليد:** {lat['generation_ms']:.0f}ms لصوت مدته "
                f"{lat['audio_duration_ms']:.0f}ms (RTF {lat['real_time_factor']:.2f})"
            )
            lines.append(f"- **الملف الصوتي:** [`{rel_path}`]({rel_path})")
            if s.notes:
                lines.append(f"- **ملاحظة:** {s.notes}")
            if r["warnings"]:
                lines.append(f"- **تحذيرات من الخادم:** {'; '.join(r['warnings'])}")
            lines.append("")

    GALLERY_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with httpx.Client() as client:
        try:
            health = client.get(f"{BASE_URL}/api/health", timeout=10.0).json()
        except httpx.ConnectError:
            print(f"Backend not reachable at {BASE_URL} — start it first (see README's Run section).")
            raise SystemExit(1)
        if health.get("status") != "ok":
            print(f"Backend not ready: {health}")
            raise SystemExit(1)

        for sample in ALL_SAMPLES:
            print(f"Generating {sample.id} ({sample.category})...")
            results.append(generate_one(client, sample))

    write_gallery(results)
    print(f"Wrote {len(results)} samples to {OUT_DIR} and {GALLERY_PATH}")


if __name__ == "__main__":
    main()
