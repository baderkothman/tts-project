# Pronunciation Correction

## The demonstrated case

**Source text**: طلب العلم فريضة على كل مسلم ومسلمة
("Seeking knowledge is an obligation upon every Muslim man and woman" — a
well-known saying)

**The ambiguity**: undiacritized العلم (root ع-ل-م) has several valid
readings in Arabic — the noun **عِلْم** (knowledge), the noun **عَلَم** (flag),
or a form of the verb **عَلِمَ** (he knew). This is not a contrived example; it
is a textbook case of Arabic orthographic ambiguity, cited independently of
this project.

**Correction technique**: targeted diacritization (tashkeel) via a
provider-independent `PronunciationRule` — `علم` → `عِلْم` — applied at the
whole-word level with definite-article clitic stripping, so `العلم` is
corrected (→ `العِلْم`) without corrupting the unrelated word `معلم` (teacher),
which merely contains the same three letters as a substring.

**Corrected text**: طلب العِلْم فريضة على كل مسلم ومسلمة

**Observed on**: provider `edge`, voice `ar-SA-ZariyahNeural`.

## What was verified, and what was not (Constitution V — full disclosure)

`scripts/observe_pronunciation.py` generated **real audio from the live Edge
provider** for both the raw and corrected text — this is not a fabricated
demo; the files exist at `docs/audio/ilm-ambiguous-before.mp3` and
`-after.mp3`.

A **byte-level comparison** of those two files confirms they are genuinely
different renderings: identical length (25,920 bytes) but **72% of bytes
differ**, proving the diacritics measurably changed what the engine
synthesized rather than being silently ignored.

**What could not be verified**: no ASR or audio-transcription tool was
available in the implementation environment (an `openai-whisper` install was
attempted and abandoned as too heavy for the sandbox; no cloud ASR
credentials were configured). This means the *specific* mispronunciation in
the "before" audio was not perceptually re-confirmed by transcription — only
that a real, measurable, provider-verified difference exists, consistent with
the documented linguistic ambiguity.

If you have working audio playback, `docs/audio/ilm-ambiguous-before.mp3` vs.
`-after.mp3` is the artifact to listen to and confirm directly. This
limitation and how to lift it are stated here rather than glossed over,
per Constitution Principle V (Measured, Not Claimed).

## Extending the pronunciation dictionary

Add a `PronunciationRule` to `backend/app/text_processing/dictionary.py`:

```python
PronunciationRule(
    original="written form",
    replacement="corrected form",
    category="person" | "company" | "place" | "product" | "medical" | "banking" | "foreign" | "ambiguous",
    locale=None,       # or e.g. "ar-SA" to scope to one locale
    provider=None,     # or e.g. "azure" for a provider-specific phoneme rule
    whole_word=True,   # False only for deliberate substring rules
    notes="why this rule exists",
)
```

Rules are pure data — extending coverage never touches `pronunciation.py`
(Constitution III, FR-018).
