# Mixed Arabic/English speech: what was actually tested, and why `native` is the default

This is the evidence behind `TTSRequest.pipeline_mode`'s default (`native`) in
`backend/app/models/tts.py`, and behind `services/english_tts.py`'s choice of Kokoro-82M as
the alternative. Every number below came from a real generation + a real ASR transcription
run during this feature's development, not from documentation claims.

## Question 1: can Lahgtna itself pronounce English at all?

Generated the sentence below three ways — once each through Kokoro-82M and through Lahgtna
directly (`language="en"` and `language=None`) — then transcribed all three with
`openai/whisper-small` and computed word error rate (WER) against the literal input text.

> "Today I have a meeting with the development team, and after that I will work on React
> and FastAPI."

| Engine | Transcript | WER |
|---|---|---|
| Kokoro-82M | "Today, I have a meeting with the development team, and after that, **I'll** work on React and **Fast API**." | 0.368 |
| Lahgtna (`language="en"`) | "Today I have a meeting with the development team and after that I will work on React and **Fast API**." | 0.105 |
| Lahgtna (`language=None`) | identical to the above | 0.105 |

Both are genuinely intelligible — nearly every "error" in both transcripts is Whisper
splitting "FastAPI" into two words or (for Kokoro) hearing a natural "I'll" contraction for
"I will," not a mispronunciation. But Lahgtna's own English, completely unprompted, already
transcribed back essentially verbatim. That's the opposite of the assumption this feature
started with (that a dedicated English model would clearly be needed), and it's the reason
Kokoro isn't the default despite being a real, working, dedicated English TTS model.

## Question 2: does that hold inside one real mixed-language sentence?

`generate()` takes one `language` value for the whole call — so the real question isn't
"can Lahgtna do English," it's "does a single Saudi-Arabic-conditioned call still pronounce
the English words inside it recognizably." Generated the task's own example sentence
through Lahgtna with `language="saudi"`/`"ars"`/`None` and transcribed each with
`openai/whisper-large-v3-turbo` (both forced-Arabic and auto-detect — identical output both
ways):

> اليوم عندي meeting مع الـ development team وبعدها رح اشتغل على React وFastAPI.

Whisper transcribed all three generations as (auto-detect):

> اليوم عندي **ميتنج** مع **الديفلوبمنت تيم** وبعدها رح اشتغل **عرياكت** وفاست **اي بي اي**

Whisper heard the embedded English words clearly enough to render them as recognizable
Arabic-script phonetic spellings — "ميتنج" for "meeting," "ديفلوبمنت تيم" for "development
team," "رياكت" for "React" (matching this project's own transliteration fallback's output
for the same word), "فاست اي بي اي" for "FastAPI." That is strong, direct evidence that one
single Lahgtna call, with no second model and no audio stitching, already produces
intelligible mixed-language speech.

## Decision

`pipeline_mode` defaults to `native` (one Lahgtna call, mixed text as-is). `dual_model`
(this evaluation's Kokoro) and `transliteration` (English converted to Arabic-script
phonetics first) are both fully implemented and selectable — the task asked for all three
as real, working options, not just the winner — but neither is the default, because:

- `dual_model` introduces a real, audible risk `native` doesn't have: a voice-identity
  switch every time the language does (Lahgtna's dialect voice vs. Kokoro's fixed English
  voice), on top of two models resident in memory and a stitching step, for a language
  Lahgtna already handles reasonably on its own.
- `transliteration` is a reasonable fallback for a term the model mispronounces (see
  `services/transliterator.py`), but converting English to Arabic-script phonetics before
  Lahgtna sees it is strictly more lossy than letting Lahgtna read the real word, when the
  evidence says it already can.

## What this evaluation does not establish

- Whisper transcribing a word back correctly is evidence of intelligibility, not of a
  convincingly *native* English accent — no native-English-speaker listening panel was run.
- Both tests used one sentence family (a tech/work-meeting register). Different vocabulary,
  especially names or terms with unusual English spelling, was not swept here — that's what
  `pronunciation_dictionary.py` and the `transliteration`/`dual_model` alternatives are for
  when `native` gets a specific term wrong.
- This compares intelligligibility, not generation latency between modes under load; both
  real end-to-end pipeline runs (`backend/tests/integration/test_mixed_language_pipeline.py`)
  completed in a few seconds per sentence on Apple Silicon (MPS), which is the only hardware
  this was measured on.
