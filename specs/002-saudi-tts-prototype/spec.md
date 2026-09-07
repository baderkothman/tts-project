# Feature Specification: Saudi Arabic TTS Prototype

**Feature Branch**: `002-saudi-tts-prototype`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Simplify the existing Arabic TTS prototype significantly. For
this phase, build only a Saudi Arabic TTS prototype: Saudi Arabic text in, Python backend,
Saudi Arabic TTS out, male/female voice, audio playback. Do not work on pronunciation
correction, diacritization, G2P, pronunciation dictionaries, STT, LLM integration, avatars,
other Arabic dialects, or complex text preprocessing. Find and implement the best practical
TTS model or API for natural Saudi Arabic, backed by real research and testing rather than
assumption."

## Relationship to the prior feature (001-arabic-tts-prototype)

This is a deliberate scope reduction, not an extension. The prior feature
(`001-arabic-tts-prototype`) built a multi-dialect, multi-provider prototype with
pronunciation correction, diacritization, a Hugging Face experimentation layer, and dialect
routing across five families. This feature starts a new, narrower phase: **Saudi Arabic
only**, with everything listed above explicitly out of scope. The codebase itself is
simplified to match — this spec does not layer onto the old one, it replaces the active
scope going forward, per explicit instruction not to let prior requirements re-expand it.

## Clarifications

### Session 2026-09-07

Provider selection was resolved by live testing performed earlier in this session, not by
question-asking, matching this project's established practice (see `001-arabic-tts-
prototype/spec.md`'s own Clarifications for precedent).

- Q: Which TTS solution should this prototype use for Saudi Arabic? → A: **Groq's Orpheus
  Arabic model (`canopylabs/orpheus-arabic-saudi`)**, hosted, as primary. It is genuinely
  Saudi/Gulf dialect-trained per vendor documentation (not Modern Standard Arabic pressed
  into service), already exposes six voices split evenly by gender (male: Abdullah, Fahad,
  Sultan; female: Lulwa, Noura, Aisha), requires only an API key (no local GPU or model
  management), and was live-tested in this session with real synthesis, real latency
  figures, and one real, vendor-undocumented constraint (10 requests/minute).
- Q: Were Hugging Face alternatives seriously evaluated, not just assumed inferior? → A:
  **Yes, tested live, not merely researched.** `NAMAA-Space/NAMAA-Saudi-TTS` (MIT license,
  Chatterbox-based) was called live through its Hugging Face Space via `gradio_client`;
  real audio was produced (~6s) and a pure-numpy pitch analysis of the output (median F0
  ≈113Hz) is consistent with a male voice. Its one bundled default reference voice does not
  give a second (female) voice for free — that would require either a reference audio clip
  this project has no right to use, or self-hosting with unverified Apple Silicon/MPS
  viability for the Chatterbox architecture. `NAMAA-Space/NAMAA-Saudi-TTS-V2` has the
  strongest documented Najdi-specific training (fine-tuned on ~18.4 hours of Najdi/Saudi
  podcast speech) but is **CC-BY-NC-SA-4.0 (non-commercial)**, disqualifying for an
  individual developer wanting freedom to eventually monetize, and requires a fresh
  reference audio clip for every single call (full voice-cloning, not a fixed-voice model)
  — a materially different, heavier integration than a fixed-voice API call.
  `AhmedEladl/Magpie-TTS-Saudi-Arabic` is a real, dedicated **female** Saudi voice
  (NVIDIA NeMo-based) but its documented inference path is CUDA-only with a heavy
  `nemo_toolkit[all]` dependency and an unconfirmed license.
- Q: Does any hosted API already used in this project (ElevenLabs) offer a genuine Saudi
  voice? → A: **No — checked live.** This account's ElevenLabs voice library (`GET
  /v1/voices`) contains zero Saudi-labeled or Arabic-labeled voices; all 21 voices are
  English-language, American/British-accented. ElevenLabs' documented "Saudi Arabic"
  support is a general multilingual-model locale capability, not a dedicated Saudi voice,
  matching this project's own earlier finding (`001-arabic-tts-prototype/docs/
  DIALECT_EVALUATION.md`).
- Q: Is Microsoft Edge Neural TTS (`ar-SA`) a candidate? → A: **No.** Prior live testing in
  this project (`001-arabic-tts-prototype`) already established Edge's `ar-SA` voice is
  MSA-trained, not Saudi-dialect-trained — it fails this feature's FR-001 (Saudi dialect,
  not MSA) by the project's own prior evidence, so it is excluded rather than re-tested.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hear Saudi Arabic Speech, Male or Female Voice (Priority: P1)

A user types conversational Saudi Arabic text, chooses a gender, picks a specific voice (or
accepts a default for that gender), and generates speech. The resulting audio plays in the
browser and sounds like natural, conversational Saudi Arabic — not formal Modern Standard
Arabic, not a different Arabic dialect.

**Why this priority**: This is the entire product for this phase. There is no secondary
capability that matters if this does not work.

**Independent Test**: Submit a Saudi conversational sentence (e.g. "وش رايك نطلع نتعشى
اليوم؟") with a male voice selected, then again with a female voice selected. Confirm both
produce audible, intelligible, distinctly-gendered Saudi Arabic speech.

**Acceptance Scenarios**:

1. **Given** Saudi Arabic conversational text and a male voice selected, **When** the user
   generates speech, **Then** intelligible audio is produced and is audibly a male voice.
2. **Given** the same text and a female voice selected, **When** the user generates speech,
   **Then** intelligible audio is produced and is audibly a female voice, audibly distinct
   from the male rendering.
3. **Given** no voice explicitly selected but a gender chosen, **When** the user generates
   speech, **Then** a voice of that gender is used and the response states which one.
4. **Given** an empty or whitespace-only submission, **When** the user requests speech,
   **Then** the user is told text is required and no audio is produced.

---

### User Story 2 - See How Long Generation Took (Priority: P2)

After generating speech, the user sees how long generation took and how that compares to
the length of the resulting audio, so the prototype's real-time viability is visible, not
just assumed.

**Why this priority**: Directly informs whether this approach could support a future
real-time use case; depends on P1 already producing audio to measure.

**Independent Test**: Generate speech and confirm the response includes a generation-time
figure, the resulting audio's duration, and their ratio.

**Acceptance Scenarios**:

1. **Given** a completed generation, **When** the user views the result, **Then**
   generation time, audio duration, and their ratio (real-time factor) are all shown.
2. **Given** a provider failure or timeout, **When** it occurs, **Then** the user sees a
   clear error rather than the service crashing or hanging indefinitely.

---

### Edge Cases

- **Empty or whitespace-only text**: rejected with a clear message; no audio produced.
- **Unknown or mistyped voice id**: rejected with an error naming the valid voice ids for
  the requested (or default) gender — never silently substituted.
- **Provider times out or errors**: reported as a clear, actionable error; the service
  keeps running and can serve the next request normally.
- **Provider rate limit hit** (a real, documented constraint of the selected provider):
  reported as a clear, actionable error distinguishable from other failures — not silently
  retried forever and not misreported as a generic failure.
- **Non-Saudi Arabic or non-Arabic text submitted**: still synthesized (this prototype does
  not attempt dialect detection or validation of the input's dialect) — the burden of
  submitting Saudi-appropriate text is on the user for this phase, consistent with keeping
  scope minimal.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST synthesize Saudi Arabic speech from Saudi Arabic text, using a
  provider with a documented, evidence-based claim to Saudi/Gulf dialect training — not a
  Modern Standard Arabic voice presented as Saudi.
- **FR-002**: System MUST expose at least one male voice and at least one female voice.
- **FR-003**: System MUST expose every additional voice the selected provider genuinely
  offers, grouped by gender, rather than arbitrarily limiting to one voice per gender.
- **FR-004**: System MUST reject empty or whitespace-only text with a clear message and
  produce no audio.
- **FR-005**: System MUST reject a voice id that does not belong to the configured
  provider, naming the valid ids for the requested gender.
- **FR-006**: System MUST return audio in a format playable in a standard browser without
  additional software.
- **FR-007**: System MUST measure and report, per request: total generation time, the
  duration of the produced audio, and the ratio between them (real-time factor).
- **FR-008**: System MUST apply an explicit timeout to every provider call and MUST report
  a provider timeout, error, or rate limit as a clear, actionable error — never a crash or
  an indefinite hang.
- **FR-009**: System MUST record a voice's gender as `"unknown"` rather than inferring or
  inventing it when the provider does not reliably document it.
- **FR-010**: Provider-specific code MUST be confined behind a small abstraction (at
  minimum: synthesize speech, list voices) so the provider could be replaced without
  changing the rest of the system — without building a larger provider-independence
  apparatus than this single-provider phase needs.
- **FR-011**: System MUST NOT use Microsoft Azure AI Speech in any capacity — not as a
  provider, a fallback, or an architecture recommendation (hard project-wide constraint,
  unchanged from `001-arabic-tts-prototype`).
- **FR-012**: System MUST NOT perform pronunciation correction, diacritization,
  grapheme-to-phoneme conversion, dialect classification/routing across multiple dialects,
  or multi-stage Arabic text preprocessing (numbers/dates/currencies/abbreviations/
  code-switching) — all explicitly out of scope for this phase.
- **FR-013**: Setup and run instructions MUST be documented precisely enough to start the
  system from a clean checkout, including which capability requires a credential.
- **FR-014**: The model/provider evaluation that led to the selected provider MUST be
  documented with real evidence (actual calls made, actual output produced or actual
  documented constraints found) for every candidate seriously considered — a candidate MUST
  NOT be dismissed on assumption alone.

### Key Entities

- **Saudi Voice**: A specific Saudi Arabic speaking identity — id, display name, provider,
  gender (`male`, `female`, or `unknown`), dialect (fixed at `saudi` for this feature), and
  the underlying model/repo identifier.
- **Speech Request**: Text to speak plus the chosen voice id (or a gender, resolved to that
  gender's default voice when no specific voice is given).
- **Generation Result**: The produced audio plus its measured generation time, audio
  duration, and real-time factor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from typing Saudi Arabic text to hearing Saudi Arabic speech in
  a single action, choosing a gender and, optionally, a specific voice.
- **SC-002**: At least one male and one female voice both produce intelligible, audibly
  gendered, real Saudi Arabic audio — verified by an actual generated recording for each,
  not asserted from provider documentation alone.
- **SC-003**: Every completed generation reports generation time, audio duration, and
  real-time factor, without exception.
- **SC-004**: 100% of induced failures (invalid voice id, empty text, provider timeout,
  provider rate limit) produce a clear, actionable error and never a crash or an
  indefinitely hanging request.
- **SC-005**: A new engineer can start the system from a clean checkout using only the
  written instructions and reach audible Saudi Arabic speech without reading source code.
- **SC-006**: The model/provider comparison names at least three real candidates evaluated
  (at least one hosted API, at least one Hugging Face model actually called or whose
  concrete constraints were actually verified) and states, for each, the specific evidence
  behind its inclusion or exclusion.

## Assumptions

- **Scope is a prototype phase, not a production service.** It runs locally for
  demonstration; multi-tenancy, accounts, billing, and persistent storage remain out of
  scope, consistent with the prior feature's own assumptions.
- **The frontend is deliberately minimal and is not a focus of this phase.** A single
  static page (text input, gender toggle, voice dropdown, generate button, audio player,
  latency display) is sufficient; no build step is required or expected.
- **The selected provider requires a credential.** Unlike the prior feature's
  credential-free default path, this phase's sole provider (Groq) requires an API key —
  acceptable for this narrower phase since the brief's own accessibility bar is "an
  individual developer," not "zero configuration."
- **Dialect authenticity is taken on the provider's documentation plus this session's live
  testing**, not on a formal native-speaker panel — no such panel was available in this
  environment, matching the prior feature's own disclosed limitation for dialect
  authenticity claims.
- **A documented, real rate limit (10 requests/minute on the selected provider) is treated
  as a known operating constraint**, not a defect to eliminate — mitigated with a bounded
  retry where practical, disclosed rather than hidden where not.
- **Multiple voices per gender are exposed because the provider genuinely offers them**
  (three male, three female) — this is not an invented requirement; it reflects what
  `canopylabs/orpheus-arabic-saudi` actually publishes.
