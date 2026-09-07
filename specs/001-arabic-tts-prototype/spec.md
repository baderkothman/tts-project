# Feature Specification: Arabic Text-to-Speech Prototype

**Feature Branch**: `001-arabic-tts-prototype`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Arabic text-to-speech prototype: a user enters Arabic text (MSA or dialect) and receives natural-sounding Arabic speech, with audio beginning to play before synthesis finishes. Must cover: Arabic text input; Modern Standard Arabic and at least one Arabic dialect; multiple selectable TTS providers compared on consistent criteria; Arabic preprocessing (Unicode/character normalization, punctuation, numbers, dates, currencies, abbreviations, Arabic-English code-switching); pronunciation correction for difficult Arabic names, ambiguous words, and foreign/brand names; emotional and speaking-style variation; provider, voice, dialect and style selection; audio playback; streaming where the provider supports it; per-stage latency measurement and time-to-first-audio; repeatable benchmarking with min/max/mean/median/P95 persisted to files; a before/after pronunciation correction demonstration using a genuinely observed defect; and an architecture that can later become a real-time Arabic conversational avatar (VAD, streaming STT, LLM, streaming TTS). Define measurable acceptance criteria."

## Clarifications

### Session 2026-09-07

Clarification for this feature was resolved by **evidence and inference rather than by
questioning**, per the explicit project direction to resolve ambiguity with sound
engineering assumptions and to avoid blocking on questions that can be safely inferred.
Each decision below is traceable to vendor documentation or to a locally executed probe;
the supporting evidence is recorded in `docs/PROVIDER_RESEARCH_NOTES.md`.

- Q: Which speech providers will be used? → A: Three adapters. **Microsoft Edge Neural TTS**
  as the credential-free primary — verified locally to expose 32 Arabic voices over 16
  Arabic locales with genuine chunked streaming, making it the one path that can be
  executed and benchmarked in every environment. **Azure AI Speech** and **ElevenLabs** as
  credential-gated adapters, each reporting itself unavailable when its key is absent.
  Azure and ElevenLabs are the two providers carried through the full written evaluation,
  with Google Cloud TTS assessed as a third comparison point.

- Q: Which Arabic locales are available? → A: The 16 Microsoft Arabic locales — ar-AE,
  ar-BH, ar-DZ, ar-EG, ar-IQ, ar-JO, ar-KW, ar-LB, ar-LY, ar-MA, ar-OM, ar-QA, ar-SA,
  ar-SY, ar-TN, ar-YE — each with one female and one male voice, confirmed by enumerating
  the live voice list. `ar-SA` serves as the Modern Standard Arabic reference. ElevenLabs
  publishes no Arabic locale codes, so its Arabic voices are catalogued without a dialect
  claim. Google exposes only `ar-XA` (Modern Standard Arabic) and therefore no dialects.

- Q: What is the dialect strategy? → A: **Locale-to-voice routing only.** A requested
  dialect selects a provider voice published for that locale. Dialect families are grouped
  for routing — Gulf, Egyptian, Levantine, Maghrebi, and MSA — so a caller may request a
  family and receive an appropriate locale. The system performs **no dialectal rewriting of
  the text itself**, and per FR-027 claims dialect support only where a provider publishes
  a distinct locale or voice.

- Q: Which providers stream, and how? → A: Edge and Azure return chunked audio over a
  persistent connection; ElevenLabs offers server-sent-event and WebSocket streaming, with
  its Flash model documented at roughly 75 ms model latency. Google's Chirp 3: HD is
  treated as non-streaming. Streaming is therefore a per-adapter declared capability, and
  any provider lacking it is served through the complete-file path instead.

- Q: What is the benchmark methodology? → A: For each provider, voice and sample, a
  discarded warm-up call is followed by a fixed number of measured repetitions. Stage
  boundaries are timed with a high-resolution monotonic clock. Min, max, mean, median and
  P95 are computed per stage, plus the ratio of generation time to produced audio duration.
  Results are written as machine-readable per-provider files plus a comparison table over
  identical samples. Runs record provider, voice, sample set and timestamp, and absolute
  figures are reported as observed on the measuring machine and network path.

- Q: Which audio formats are used? → A: **MP3 at 24 kHz mono** as the default, because it
  is both progressively playable in a browser and safe to stream chunk-by-chunk, letting
  the streaming requirement be demonstrated without client-side audio assembly. Raw PCM and
  Opus are exposed where a provider supports them, for lower-latency and
  telephony-oriented use, and are documented for the eventual avatar pipeline.

- Q: What is the frontend choice? → A: A **single static HTML and JavaScript page served by
  the Python backend**, with no build step. This is chosen over a notebook-style UI
  framework for one substantive reason: a plain audio element pointed at a streaming
  endpoint begins playback as the first bytes arrive, so it demonstrates streaming
  honestly, whereas a framework that hands the player a completed buffer would conceal the
  very property being demonstrated. The page carries no domain logic.

- Q: What is the pronunciation correction strategy? → A: **Provider-independent
  orthographic rewriting is primary** — targeted diacritization, phonetic respelling, and
  alias substitution applied to the text before synthesis. This is forced by the evidence:
  ElevenLabs restricts phoneme tags to English, and Google's Chirp 3: HD accepts no markup
  at all, so no phoneme-based approach is portable across providers. Markup-based
  correction using SSML phoneme tags is therefore implemented only as a
  capability-gated enhancement for providers that declare support for it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hear Arabic Text Spoken Aloud (Priority: P1)

An Arabic-speaking user pastes or types a passage of Arabic text, presses a single action,
and hears it spoken in a natural Arabic voice. Playback begins while the rest of the
passage is still being generated, so the user is not left waiting in silence.

**Why this priority**: This is the irreducible core of the product. Without it there is no
prototype. Every other story is an enhancement of, or a measurement of, this one.

**Independent Test**: Enter a paragraph of Modern Standard Arabic, request speech, and
confirm audible, intelligible Arabic speech is produced and begins playing before the full
passage has finished generating. Delivers standalone value as a working Arabic reader.

**Acceptance Scenarios**:

1. **Given** a passage of Modern Standard Arabic text, **When** the user requests speech,
   **Then** intelligible Arabic audio is produced covering the entire passage.
2. **Given** a passage long enough to take several seconds to synthesize, **When** the user
   requests speech, **Then** the first audio becomes audible before the final portion of
   the passage has been generated.
3. **Given** an empty submission, **When** the user requests speech, **Then** the user is
   told that text is required and no audio is produced.
4. **Given** text exceeding the permitted length, **When** the user requests speech,
   **Then** the user is told the limit and the actual length, and no partial audio is
   silently produced.

---

### User Story 2 - Correct Pronunciation of Difficult Arabic Text (Priority: P1)

A user submits Arabic text containing digits, dates, amounts of money, abbreviations,
embedded English words, and ambiguous or unusual Arabic words. The system speaks all of it
correctly as Arabic words — not as digit strings, spelled-out letters, or mispronounced
guesses — and the user can see exactly what text was actually spoken.

**Why this priority**: Equal to P1 because raw Arabic TTS reliably fails on precisely this
content, and this failure is what separates a demo from a usable product. A system that
reads "1,250.50 دولار" as disconnected digits is not usable for banking, retail, or news.

**Independent Test**: Submit the documented difficult-content sample set and confirm each
category is verbalized as correct Arabic words, with the processed text viewable alongside
the original. Delivers standalone value even without provider choice or benchmarking.

**Acceptance Scenarios**:

1. **Given** text containing `125`, `1,250`, `25.5`, and `75%`, **When** speech is
   requested, **Then** each is spoken as Arabic words rather than as individual digits.
2. **Given** text containing `27/09/2026` and `2026-09-27`, **When** speech is requested,
   **Then** each is spoken as a spoken-form Arabic date, not as separated numbers.
3. **Given** text containing `$25` and `1,250.50 دولار`, **When** speech is requested,
   **Then** the amount and its currency are spoken as Arabic words in the correct order.
4. **Given** text mixing Arabic and English such as a meeting time with an English term,
   **When** speech is requested, **Then** both the Arabic and the embedded English are
   intelligible and the sentence is not broken by the language switch.
5. **Given** any submission, **When** speech is produced, **Then** the user can view both
   the original text and the final processed text that was sent for synthesis.
6. **Given** a word the engine pronounces incorrectly and for which a correction rule
   exists, **When** speech is requested, **Then** the corrected pronunciation is heard.

---

### User Story 3 - Compare Providers, Voices, Dialects and Styles (Priority: P2)

A user selects among multiple speech providers, among Arabic voices including at least one
regional dialect distinct from Modern Standard Arabic, and among speaking styles such as
neutral, warm, or excited. The same sentence can be rendered repeatedly under different
selections so the user can judge which combination sounds best.

**Why this priority**: Establishes provider independence and dialect capability, which are
central to the product thesis, but the system delivers value with a single provider first.

**Independent Test**: Render one identical sentence across each available provider, at
least two distinct Arabic locales, and at least two styles, then compare the results.

**Acceptance Scenarios**:

1. **Given** more than one configured provider, **When** the user views the options,
   **Then** each provider is listed with its availability state, and providers lacking
   credentials are shown as unavailable rather than being silently missing or erroring.
2. **Given** a selected provider, **When** the user views voices, **Then** only voices that
   provider actually offers are listed, each with its locale and dialect.
3. **Given** a dialect selection with no explicit voice, **When** speech is requested,
   **Then** a voice appropriate to that dialect is chosen automatically and the response
   states which voice was used.
4. **Given** a requested style the selected voice cannot express, **When** speech is
   requested, **Then** the system either renders the nearest supported approximation or
   reports the style as unsupported — it never silently ignores the request.
5. **Given** a requested locale no provider supports, **When** speech is requested,
   **Then** the user receives an error naming the supported locales.

---

### User Story 4 - Measure and Compare Latency (Priority: P2)

A user or engineer sees, for each synthesis, how long each stage took — text processing,
provider response, time until the first audio was available, and total generation time —
and can run a repeatable benchmark across a fixed sample set that reports distribution
statistics and writes them to a file for later comparison.

**Why this priority**: Latency is the stated gating requirement for the eventual real-time
avatar, and unmeasured latency cannot be optimized. It depends on P1 existing first.

**Independent Test**: Run the benchmark across the sample set and confirm a results file is
written containing per-stage timings and min, max, mean, median and P95 aggregates.

**Acceptance Scenarios**:

1. **Given** any completed synthesis, **When** the user inspects the result, **Then**
   per-stage timings including time-to-first-audio and total generation time are reported.
2. **Given** a benchmark run over a fixed sample set with repetitions, **When** it
   completes, **Then** min, max, mean, median and P95 are reported for each measured stage.
3. **Given** a completed benchmark run, **When** the user looks at the stored output,
   **Then** a results file exists recording the provider, voice, sample set and timestamp
   that produced the numbers.
4. **Given** benchmark runs for two providers, **When** the user compares them, **Then** a
   side-by-side comparison over the same samples and the same criteria is available.
5. **Given** a synthesis, **When** timings are reported, **Then** the ratio of generation
   time to produced audio duration is available, so real-time feasibility can be judged.

---

### User Story 5 - Demonstrate a Pronunciation Fix Before and After (Priority: P3)

A user sees a specific, genuinely observed case where the speech engine mispronounces
Arabic text, hears the incorrect rendering, sees what the correct pronunciation should be
and what correction was applied, and hears the corrected rendering.

**Why this priority**: A persuasive proof of the pronunciation-control capability, but it
demonstrates machinery that Story 2 already delivers.

**Independent Test**: Open the demonstration, play both renderings of the same source text,
and confirm they differ audibly in the described way.

**Acceptance Scenarios**:

1. **Given** the demonstration case, **When** the user views it, **Then** the original
   text, the observed incorrect pronunciation, the intended pronunciation, and the
   correction technique used are all stated.
2. **Given** the demonstration case, **When** the user requests both renderings, **Then**
   uncorrected and corrected audio are both produced from the same source text.
3. **Given** the demonstration case, **When** its documentation is read, **Then** the
   defect is recorded as observed from an actual synthesis, including which voice and
   provider exhibited it, rather than asserted hypothetically.

---

### Edge Cases

- **Empty or whitespace-only text**: rejected with a clear message; no audio produced.
- **Text over the length limit**: rejected stating the limit and the submitted length.
- **Text containing no Arabic at all** (pure English or pure digits): still synthesized,
  since mixed and foreign content is expected; no crash and no silent empty audio.
- **Text with existing diacritics (tashkeel)**: preserved, not stripped, so the author's
  intended pronunciation survives processing.
- **Markup-like or control characters embedded in user text**: treated strictly as literal
  text to be spoken; they can never alter the synthesis instructions sent to the provider.
- **Provider times out or returns an error mid-stream**: a configured alternative is
  attempted; the response records that a substitution occurred and which provider served it.
- **No provider is available at all** (no credentials configured): the user is told clearly
  which providers exist and what is required to enable them; the system remains running.
- **Requested voice does not belong to the selected provider**: rejected with an error
  identifying valid voices rather than falling back silently to an unrelated voice.
- **Requested locale has no voice**: rejected with an error listing supported locales.
- **Dialect family requested that the selected provider cannot serve**: resolved against
  another available provider, or rejected naming the families that provider does serve —
  never quietly downgraded to Modern Standard Arabic.
- **Client disconnects mid-stream**: synthesis is abandoned promptly rather than continuing
  to consume provider quota.
- **Ambiguous undiacritized word with several valid readings**: the system does not guess
  silently; the reading is either governed by an explicit rule or left to the engine, and
  which occurred is inspectable.
- **Numbers that are identifiers, not quantities** (such as a phone number): spoken as a
  sequence of digits rather than as a single large cardinal quantity.

## Requirements *(mandatory)*

### Functional Requirements

**Input and synthesis**

- **FR-001**: System MUST accept Arabic text input and produce audible Arabic speech from it.
- **FR-002**: System MUST support Modern Standard Arabic and at least one distinct regional
  Arabic dialect, each with at least one voice.
- **FR-003**: System MUST reject empty, whitespace-only, and over-length input with a
  message that states the reason and, for length, the limit and the submitted length.
- **FR-004**: System MUST return audio in a format playable in a standard browser without
  additional software.

**Arabic text processing**

- **FR-005**: System MUST apply Unicode normalization and remove invisible and control
  characters that would otherwise corrupt synthesis.
- **FR-006**: System MUST normalize Arabic presentation forms, elongation (tatweel), and
  inconsistent punctuation without altering word meaning.
- **FR-007**: System MUST NOT fold hamza forms, taa marbuta, or alif maqsura into their
  bare equivalents in the text submitted for synthesis, as doing so changes pronunciation.
- **FR-008**: System MUST preserve diacritics already present in the input.
- **FR-009**: System MUST verbalize cardinal numbers, decimals, and percentages as Arabic
  words.
- **FR-010**: System MUST verbalize dates written in numeric and mixed formats as spoken
  Arabic dates.
- **FR-011**: System MUST verbalize currency amounts as Arabic words with the currency
  named in the correct position relative to the amount.
- **FR-012**: System MUST expand or correctly render Arabic and Latin abbreviations,
  including initialisms that should be spelled out and those that should be read as words.
- **FR-013**: System MUST handle text mixing Arabic and English so that both are
  intelligible and sentence flow is preserved.
- **FR-014**: System MUST treat long digit sequences that identify rather than quantify,
  such as telephone numbers, as digit sequences rather than as single quantities.
- **FR-015**: System MUST expose both the original and the final processed text for any
  synthesis, so the transformation is inspectable.
- **FR-016**: Each processing stage MUST be individually testable and MUST be able to be
  reported on independently.

**Pronunciation control**

- **FR-017**: System MUST support declarative pronunciation rules that map a written form
  to a corrected form, scoped optionally by locale and by provider.
- **FR-018**: Pronunciation rules MUST be stored as data that can be extended without
  changing program logic, and MUST accommodate people's names, organization and product
  names, places, and domain vocabulary such as medical and banking terms.
- **FR-019**: System MUST record, for at least one genuinely observed mispronunciation, the
  original text, the observed rendering, the intended rendering, the correction applied,
  and the voice and provider on which it was observed.
- **FR-020**: System MUST be able to produce both uncorrected and corrected audio for the
  same source text so the two can be compared directly.

**Providers, voices and routing**

- **FR-021**: System MUST support more than one speech provider and MUST allow the user to
  choose which one serves a request.
- **FR-022**: System MUST allow a provider to be added or removed without changes to text
  processing, routing, or application logic.
- **FR-023**: System MUST publish, per provider, which capabilities it supports —
  streaming, styles, pronunciation markup, and available locales — as queryable data
  rather than as documentation only.
- **FR-024**: System MUST report a provider whose credentials are absent as unavailable and
  MUST exclude it from automatic routing, while continuing to serve other providers.
- **FR-025**: System MUST select an appropriate voice automatically when a dialect or
  locale is requested without an explicit voice, and MUST report which voice it selected.
- **FR-025a**: System MUST accept a dialect *family* — Modern Standard, Gulf, Egyptian,
  Levantine, or Maghrebi — as an alternative to an exact locale, and MUST resolve it to a
  concrete supported locale and voice, reporting both in the response.
- **FR-026**: System MUST reject a voice that does not belong to the selected provider, and
  an unsupported locale, with an error naming valid alternatives.
- **FR-027**: System MUST NOT present a dialect as supported by a provider unless that
  provider offers a distinct voice or locale for it.
- **FR-028**: System MUST accept a requested speaking style and MUST either render it,
  render a documented approximation, or report it as unsupported for that voice — never
  ignore it silently.

**Streaming, latency and reliability**

- **FR-029**: System MUST stream audio to the client incrementally where the serving
  provider supports incremental synthesis, forwarding the first audio as it arrives rather
  than waiting for completion.
- **FR-030**: System MUST offer a complete-file synthesis path in addition to streaming,
  for providers or clients that cannot stream.
- **FR-031**: System MUST measure and report, per request: text-processing duration,
  time until the provider returned its first audio, time until the first audio was sent to
  the client, total generation duration, and the duration of the audio produced.
- **FR-032**: System MUST apply an explicit time limit to every provider call.
- **FR-033**: System MUST attempt a configured alternative provider when the primary fails
  or times out, and MUST record in the response that a substitution occurred.
- **FR-034**: System MUST remain available when a provider fails; a provider error MUST NOT
  terminate the service.

**Benchmarking**

- **FR-035**: System MUST run a repeatable benchmark over a fixed Arabic sample set with a
  configurable number of repetitions.
- **FR-036**: Benchmarks MUST report min, max, mean, median and P95 for each measured stage.
- **FR-037**: Benchmark output MUST be written to files recording provider, voice, sample
  set, and timestamp, and MUST support side-by-side comparison of providers over identical
  samples and criteria.
- **FR-038**: System MUST provide a reusable Arabic sample set covering Modern Standard
  Arabic, dialect, difficult pronunciation, numbers, dates, currencies, abbreviations,
  code-switching, and style variation.
- **FR-038a**: Each sample in the difficult-content categories MUST carry a stated expected
  transformation, so that SC-003 can be asserted per sample rather than judged by eye.
  (Closes CHK004.)

**Security and privacy**

- **FR-039**: Provider credentials MUST be supplied through the environment, MUST never
  appear in any response, and MUST never be committed to the repository.
- **FR-040**: User-submitted text and generated audio MUST NOT be logged or retained by
  default.
- **FR-041**: User text MUST NOT be able to alter the instructions sent to a provider; any
  markup-like content in user text MUST be treated as literal text to be spoken.
- **FR-042**: All requests MUST be schema-validated with enforced limits before processing.
- **FR-042a**: A rate-limiting strategy MUST be defined, stating explicitly whether it is
  implemented in this prototype or documented as production architecture, so that its
  status is never ambiguous. (Closes CHK052.)

**Evaluation and documentation**

- **FR-043**: At least two speech providers MUST be evaluated against a single consistent
  set of criteria covering Arabic quality, dialect coverage, pronunciation control, style
  control, code-switching, streaming, latency, voice selection, customization, interface
  quality, cost, and production limits.
- **FR-044**: The evaluation MUST issue explicit recommendations for best Arabic quality,
  best real-time suitability, best pronunciation control, best dialect support, and best
  cost-to-quality balance, each traceable to cited evidence.
- **FR-045**: At least one provider MUST be integrated and verified end to end.
- **FR-046**: The evolution of this prototype into a real-time conversational avatar —
  covering voice activity detection, streaming speech recognition, language model
  response, response chunking, streaming synthesis, interruption handling, session state,
  scaling, observability, and privacy — MUST be documented, including where latency
  accumulates and how it can be reduced.
- **FR-047**: Setup and run instructions MUST be documented precisely enough to start the
  system from a clean checkout, including which capabilities require credentials.

### Key Entities

- **Speech Request**: Text to speak plus the choices governing how — locale or dialect,
  provider, voice, speaking style, speaking rate, pitch, and audio format — together with
  whether pronunciation processing should be applied.
- **Processed Text**: The result of the transformation pipeline, retaining the original
  text, the final text submitted for synthesis, and a record of which stages changed it.
- **Voice**: A specific speaking identity offered by a provider, with its language, locale,
  dialect, gender, and the capabilities it supports, plus a designated alternative to use
  when it is unavailable.
- **Provider Capability Descriptor**: The declared abilities of a provider — streaming,
  styles, pronunciation markup, supported locales and formats, and character limits.
- **Pronunciation Rule**: A mapping from a written form to a corrected written or phonetic
  form, optionally scoped to a locale or a provider, with a note recording why it exists.
- **Latency Trace**: The ordered stage timestamps for a single synthesis and the durations
  derived from them.
- **Benchmark Result**: The aggregated timings for one provider and voice over one sample
  set, with the distribution statistics and the run's identifying metadata.
- **Arabic Sample**: A reusable labelled test text, tagged with the category it exercises
  and the behavior expected of it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from entering Arabic text to hearing Arabic speech in a single
  action, with no configuration required beyond defaults.
- **SC-002**: For a passage of at least 200 Arabic characters, audio becomes audible to the
  user before synthesis of the passage has completed, in at least 9 of 10 attempts.
- **SC-003**: Every category in the difficult-content sample set — numbers, dates,
  currencies, percentages, abbreviations, code-switching, identifier digit strings — is
  verbalized as correct spoken Arabic, with 100% of the documented sample cases passing
  their stated expected transformation.
- **SC-004**: Text processing adds no more than 50 milliseconds at the 95th percentile for
  a 500-character passage, so it is never the dominant contributor to perceived delay.
- **SC-005**: At least two distinct Arabic locales, of which at least one is a regional
  dialect rather than Modern Standard Arabic, can be selected and produce audibly different
  speech from the same input text.
- **SC-006**: At least three speaking-style selections produce measurably different audio
  from the same input text, or are explicitly reported as unsupported for the chosen voice.
- **SC-007**: A benchmark over the sample set completes and writes files containing min,
  max, mean, median and P95 for every measured stage, and the run can be repeated to
  produce comparable output.
- **SC-008**: The recorded pronunciation demonstration produces two audibly different
  renderings of the same source text, and its documentation identifies the voice and
  provider on which the defect was observed.
- **SC-009**: A provider failure or timeout results in either successful audio from an
  alternative provider or an actionable error, in 100% of induced-failure tests, and never
  in a terminated service.
- **SC-010**: Adding a hypothetical new provider requires changes only within that
  provider's own adapter and its registration, verified by inspection of module boundaries.
- **SC-011**: No credential value appears in any response payload, log line, or committed
  file, verified by an automated check over the repository and over captured responses.
- **SC-012**: Markup-like content submitted as user text is spoken as literal text and
  never changes the synthesis instructions, verified by explicit tests.
- **SC-013**: A new engineer can start the system from a clean checkout using only the
  written instructions, and reach audible Arabic speech without consulting source code.
- **SC-014**: The provider evaluation covers at least two providers on all stated criteria
  and every capability claim is traceable to a cited source or a recorded observation.
- **SC-015**: The automated test suite runs to completion without requiring provider
  credentials, and tests that require credentials are skipped rather than failing.

## Assumptions

- **Scope is a prototype, not a hosted product.** It runs locally for demonstration.
  Multi-tenancy, user accounts, billing, and persistent storage are out of scope.
- **The demonstration interface is deliberately minimal.** It exists to exercise and reveal
  the pipeline; visual design is explicitly not a goal, and no capability lives only in it.
- **A single concurrent user is assumed.** Load, autoscaling, and quota-sharing behavior are
  documented as future architecture rather than built and load-tested now.
- **Provider credentials may be absent.** Because paid credentials cannot be assumed, at
  least one provider path must work without them, and credential-requiring providers must
  degrade to an "unavailable" state rather than blocking the prototype. Capabilities that
  genuinely cannot be exercised without credentials are documented as such.
- **Dialect support means what the provider documents.** Dialect coverage is limited to
  locales a provider actually publishes; convincing dialect rendering beyond that, such as
  dialect-specific text rewriting, is out of scope.
- **Speaking style may be approximated.** Where Arabic voices expose no native emotional
  style control, style is mapped onto available prosody controls, and this approximation is
  documented rather than presented as native emotional synthesis.
- **Automatic diacritization is optional and off by default.** Full automatic tashkeel
  requires a specialized model whose cost and accuracy are not justified here; explicit
  pronunciation rules cover the targeted cases instead.
- **Latency figures are environment-dependent.** Benchmarks measure this machine and its
  network path to the provider; absolute numbers are reported as observed, and comparisons
  between providers are made only within a single run environment.
- **Audio is not retained.** Generated audio is streamed or returned and not persisted,
  except for explicitly saved demonstration and benchmark artifacts.
- **The avatar pipeline is documented, not built.** Voice activity detection, speech
  recognition, and language model integration are architecture deliverables for this
  feature, not running code.
