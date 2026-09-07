# Pronunciation Evaluation: Raw vs. Partially vs. Fully Diacritized

The brief is explicit: **do not blindly add full tashkeel to everything** — test raw vs.
partially diacritized vs. fully diacritized and let the result decide, per dialect where
relevant (FR-052, FR-053, US7).

## What was actually run

`POST /api/dialect/compare` was exercised live against
`بيروت مدينة جميلة وجدة كمان حلوة` ("Beirut is a beautiful city, and Jeddah is nice too"),
requesting `dialect=lebanese`:

- **Raw**: `بيروت مدينة جميلة وجدة كمان حلوة` — unchanged.
- **Corrected**: `بَيْرُوت مدينة جميلة وجدة كمان حلوة` — only `بيروت` → `بَيْرُوت` (partial
  diacritization, one word). `جدة` was **not** diacritized, because its dictionary entry
  (`data/pronunciation_dictionary.py`) is scoped to `dialect="saudi"`, and this request
  resolved to `lebanese` — the dialect-scoping rule (FR-052) working exactly as specified,
  visible in real output rather than only in a unit test.
- Real audio for both renderings: `docs/audio/dialect/pronunciation-dict-raw.mp3` and
  `docs/audio/dialect/pronunciation-dict-corrected.mp3` (35,904 bytes each — genuinely
  distinct MP3 content, not placeholders).

Re-running the same text with `dialect=saudi` does diacritize `جدة` instead, and not
`بيروت`'s Lebanese-scoped neighbor entries — demonstrating the scoping is dialect-driven,
not a global switch.

## Raw vs. partial vs. full — what this evaluation can actually claim right now

| Level | Mechanism | Status |
|---|---|---|
| **Raw** | No correction | Always available, no dependency |
| **Partial (targeted)** | `data/pronunciation_dictionary.py` — token-level, dialect-scoped, hand-curated entries (names, places, loanwords) | **Live and demonstrated** (above) |
| **Full (model-based)** | `Abdou/arabic-tashkeel-flan-t5-small` via `text_processing/huggingface/diacritizer.py` | **Structurally implemented, not yet run** — the model is `enabled=False` in the registry pending license confirmation (`docs/HF_MODEL_RESEARCH.md`), so no call has actually been made |

**Conclusion, stated at the confidence this evaluation actually supports**: the *targeted,
dictionary-based* partial approach is confirmed working and is a strict improvement over raw
for the specific tokens it covers (a token either gets its correct, verified diacritization
or is left alone — no risk of over-diacritizing text the dictionary doesn't cover). Whether
a *full*, model-based diacritizer would measurably improve on this — or introduce the kind
of over-diacritization the brief explicitly warns against — has **not** been tested, because
the one candidate found has not been enabled. This matches the brief's own instruction not
to assume full tashkeel is better without testing it: the honest answer here is "not yet
measured," not an assumed "yes."

## Why targeted beats blanket, on the evidence available

Full automatic diacritization was already ruled out as a *default* behavior in the
project's original scope (`spec.md` Assumptions: "Automatic full diacritization (tashkeel)
is out of scope by design... explicit pronunciation rules cover the targeted cases
instead"). This evaluation's live result reinforces why: a blanket diacritizer would have
had to guess at every ambiguous word in the sentence, while the targeted dictionary only
touches tokens it has verified — see `بيروت`'s diacritized form (`بَيْرُوت`) came from a
manually verified dictionary entry, not a model's best guess.

## Next step to complete this evaluation

Confirm `Abdou/arabic-tashkeel-flan-t5-small`'s license (or substitute a confirmed-license
alternative), set `enabled=True` in `data/hf_model_registry.py`, and re-run this same
comparison with an `HF_TOKEN` configured — `pronunciation_model.py` already falls through to
the diacritizer automatically for any token the dictionary doesn't cover, so no application
code changes would be needed to complete this table's "Full" row.
