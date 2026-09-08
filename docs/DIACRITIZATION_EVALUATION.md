# Arabic diacritization: model selection and two measured, reproduced defects

The full reasoning also lives in `backend/app/services/diacritizer.py`'s module
docstring; this doc is the companion evidence log (Constitution V: measured, not claimed).

## Candidates considered

| Candidate | Why not chosen |
|---|---|
| Hand-written diacritization rules | Explicitly out of scope per the task brief — Arabic grammar/morphology rules are exactly what a dedicated model does better than a rule set built for this prototype. |
| CATT (character-attention Tashkeel transformer) | Real, well-regarded, Apache-2.0 as of its latest release — but ships checkpoints as GitHub Release assets rather than a Hugging Face Hub repo `transformers` can load directly, and needs its own `catt-tashkeel` package. Passed over for integration simplicity, not quality. |
| `Etherll/Tashkeel-350M-v2` | A genuinely more modern (2025) base (Granite-4.0-h), but it's an instruction-tuned causal LM prompted with "قم بتشكيل هذا النص: …" — a chat-style model can rephrase or drop text, which is a real risk for a diacritizer whose contract is "add marks, change nothing else." No published DER/WER on its model card to weigh against that risk. |
| **`basharalrfooh/Fine-Tashkeel`** (chosen) | A plain ByT5 `AutoModelForSeq2SeqLM` fine-tuned specifically for diacritic restoration on the Tashkeela corpus — nothing but `transformers` needed, MIT-licensed, and its model card publishes DER 0.95% / WER 2.49%, a real number, not a bare claim. |

## Two real defects found by actually running it, both handled in code

**1. Feeding it already-diacritized text corrupts the output.** Tested directly:

```
IN:  اَلسَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللهِ
OUT: اَلسََّّلِيَامُُ عَلَيْْكُمْْ وََرَََحْْمَيَةُُ اللَّهِِ
```

Doubled shaddas and dammas, not a cosmetic artifact — a second diacritization pass on
already-marked text actively breaks it. `diacritize()` checks `has_diacritics()` first and
passes such input through untouched. This turns the task's "preserve user diacritics"
requirement from a politeness rule into a correctness fix.

**2. On real dialectal input, the model appends full MSA grammatical case endings
(i'rab) to colloquial words that aren't inflected that way in speech.** Tested on real
Lebanese and Gulf sentences:

| Dialect | Input word | Model output | Problem |
|---|---|---|---|
| Lebanese | روح ("go") | رُوحٍ | Genitive-case tanween — reads as the noun "spirit/soul[gen]," not the colloquial verb. |
| Lebanese | بدي ("I want") | بَدِيُّ | Spurious doubled/case ending not present in speech. |
| Gulf | وش ("what") | وَشِّ | Same pattern. |
| Gulf | نروح ("we go") | نَرُوحُ | MSA imperfect-indicative ending (-u) that colloquial speech drops. |

Fix: for any `dialect_id != "msa"`, `diacritize()` strips only the word-final
short-vowel/tanween mark (`_strip_word_final_irab`) — never sukun (no vowel — harmless
either way) and never shadda (real gemination, e.g. dialectal "عمّ" ('amma) needs its
doubled م kept). Verified against the same four examples: "رُوحٍ" -> "رُوح", "بَدِيُّ" ->
"بَدِيّ" (gemination kept), "وَشِّ" -> "وَشّ" (same), "نَرُوحُ" -> "نَرُوح" — the case-ending
artifact is gone, stem vowels and real gemination survive.

## What this does not claim

- This is a targeted fix for one observed failure mode (spurious case endings), not a
  general dialectal-Arabic diacritizer — the model's stem-vowel choices for dialectal
  words are still MSA-trained guesses, just no longer topped with an invented ending.
- No native-speaker rating panel scored the corrected output; the evidence here is the
  specific reproduced-and-fixed defect above, not an overall quality claim.
