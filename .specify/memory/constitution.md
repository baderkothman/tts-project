<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Rationale: Initial ratification. First constitution for the Arabic TTS prototype.

Modified principles: none (initial adoption)

Added principles:
  - I. Python-First Backend
  - II. Provider Independence
  - III. Arabic Linguistic Correctness
  - IV. Latency Is A Feature
  - V. Measured, Not Claimed
  - VI. Graceful Degradation
  - VII. Secure By Default
  - VIII. Testability And Simplicity

Added sections:
  - Additional Constraints (Arabic Speech Domain)
  - Development Workflow & Quality Gates
  - Governance

Removed sections: none

Template note: the resolved constitution scaffold carries five principle slots. The
project owner specified eight principles, so the Core Principles section was extended
to eight per the "respect the specified number" rule. Heading hierarchy is unchanged.

Follow-up TODOs: none. No placeholder tokens remain.
-->

# Arabic TTS Prototype Constitution

## Core Principles

### I. Python-First Backend

All backend logic MUST be implemented in Python: Arabic text preprocessing, TTS provider
integration, provider abstraction, dialect and voice routing, streaming, benchmarking,
latency instrumentation, and every business rule. The frontend is a demonstration surface
only. No architectural decision may be made to suit a frontend framework, and no domain
logic — including text normalization, voice selection, and metric computation — may live
in frontend code. If a capability is needed by the UI, it MUST be exposed by the Python
API rather than reimplemented client-side.

Rationale: the prototype's value is the Python pipeline that a production Arabic
conversational avatar will later reuse. A capability implemented in the UI is a capability
that must be rewritten.

### II. Provider Independence

Vendor-specific code MUST be confined to adapter classes implementing a single abstract
`TTSProvider` interface. Application, routing, and preprocessing layers MUST NOT import a
provider SDK, reference a provider-specific model or response object, or branch on a
provider name to make a domain decision. Provider capabilities MUST be declared as data
through a capability descriptor and consumed generically. Adding or removing a provider
MUST require no change outside its adapter and its registration.

Rationale: Arabic TTS quality, pricing, and dialect coverage differ sharply between
vendors and change often. The system must be able to switch or compare providers without
a rewrite.

### III. Arabic Linguistic Correctness

Arabic text processing MUST preserve meaning. Normalization MUST NOT collapse
distinctions that change a word's sense or grammatical role. Specifically, hamza forms
(أ/إ/آ/ا), taa marbuta (ة/ه), and alif maqsura (ى/ي) MUST NOT be folded together in the
text sent to a TTS engine, because that folding is a search-and-retrieval technique that
corrupts pronunciation. Existing diacritics (tashkeel) MUST be preserved unless a rule
deliberately replaces them. Every pronunciation correction MUST be expressed as data —
a declarative rule with an explicit scope — never as an inline code branch. Each
transformation stage MUST be independently inspectable so that a raw-versus-processed
comparison can be shown.

Rationale: over-normalization is the most common and most damaging error in Arabic NLP
pipelines, and it silently degrades speech output rather than failing loudly.

### IV. Latency Is A Feature

All I/O MUST be asynchronous and non-blocking. Where a provider supports streaming
synthesis, the system MUST stream: the first audio chunk MUST be forwarded to the client
as it arrives, and the pipeline MUST NOT wait for synthesis to complete before emitting
data. Blocking calls MUST NOT occur on the event loop. Time-to-first-audio MUST be
instrumented at every stage boundary using a high-resolution monotonic clock, and the
resulting timings MUST be retrievable per request.

Rationale: the prototype is the first stage of a real-time conversational avatar, where
perceived latency, not total generation time, determines whether the experience works.

### V. Measured, Not Claimed

Every performance, quality, or capability assertion in code comments, documentation, or
final reporting MUST be backed by a recorded benchmark run or an executed test. Provider
capabilities — dialect support, streaming, emotional control, phoneme control — MUST NOT
be asserted from marketing material; they MUST be traced to vendor documentation or
verified by execution, and the source MUST be cited. Benchmark results MUST be persisted
as files with the sample set, provider, voice, and timestamp that produced them. A
demonstrated pronunciation defect MUST be an actually observed defect, never a
hypothetical one.

Rationale: an Arabic TTS evaluation is only useful if its numbers are reproducible and
its claims are falsifiable.

### VI. Graceful Degradation

Provider failure, timeout, rate limiting, or missing credentials MUST degrade the system,
never crash it. Every provider call MUST carry an explicit timeout. A configured fallback
MUST be attempted when the primary provider fails, and the response MUST record that a
fallback occurred. A provider whose credentials are absent MUST be reported as
unavailable and excluded from routing rather than raising at import or startup. An
unsupported locale, voice, or capability MUST produce an actionable error naming the
supported alternatives.

Rationale: a multi-provider system exists precisely so that one vendor's outage is
survivable; a hard dependency on any single provider forfeits that benefit.

### VII. Secure By Default

Provider credentials MUST be read from environment variables only, MUST NOT be committed,
and MUST NOT be returned by any API response or written to any log. A `.env.example`
carrying names but no values MUST be maintained. All request bodies MUST be validated by
schema, with enforced input-length limits. SSML MUST be constructed programmatically with
all interpolated text escaped, so that markup injection through user text is prevented by
construction rather than by filtering. User-supplied text and generated audio MUST NOT be
logged or persisted by default.

Rationale: the pipeline handles user speech content and paid third-party credentials;
both are attractive targets and neither is recoverable once leaked.

### VIII. Testability And Simplicity

Text-processing stages MUST be pure functions — deterministic, side-effect free, and
testable without network access. The default test suite MUST NOT make live paid provider
calls; provider integration tests MUST be separately marked and skipped when credentials
are absent. The simplest design that meets the requirement MUST be chosen: deterministic
code before a model call, a single call before a workflow, a workflow before an agent.
Frameworks, queues, vector stores, and additional services MUST NOT be introduced without
a demonstrated need recorded in the plan.

Rationale: the prototype must stay legible and verifiable; complexity added early is
complexity that must be maintained before it has earned its place.

## Additional Constraints (Arabic Speech Domain)

- The system MUST support Modern Standard Arabic and at least one Arabic dialect, and
  MUST NOT claim dialect support for a provider that does not document a distinct locale
  or voice for that dialect.
- Text processing MUST handle, as distinct and separately testable concerns: Unicode and
  Arabic character normalization, punctuation, numbers, dates, currencies, abbreviations,
  Arabic–English code-switching, and pronunciation rules.
- Number, date, and currency verbalization MUST produce Arabic words appropriate to the
  target locale rather than relying on the engine's own digit handling.
- Emotional or speaking-style control MUST be expressed in the normalized request model
  and translated per provider. Where a provider's Arabic voices expose no style parameter,
  the adapter MUST either map style to supported prosody controls or declare the
  capability unsupported. It MUST NOT silently ignore the request.
- Audio format selection MUST be explicit and MUST account for streaming suitability.
- At least two providers MUST be evaluated against consistent criteria, and at least one
  MUST be integrated and verified end to end.

## Development Workflow & Quality Gates

- Planning artifacts — constitution, specification, plan, tasks — MUST exist and be
  mutually consistent before implementation begins, and MUST be retained in the
  repository as deliverables.
- A task MUST NOT be marked complete because code exists for it; its stated acceptance
  criteria MUST be verified.
- Before completion, the test suite MUST be run and its real result reported. Failures
  MUST be stated plainly, including which are pre-existing or unrelated.
- Any check that was not run, or could not be run, MUST be reported as not run. Claiming
  an unexecuted result is prohibited.
- Documentation MUST reflect final behavior, including known limitations.

## Governance

This constitution supersedes other practices for this project. Where a more specific
instruction file sits nearer to the files being changed, the more local instruction wins
except on safety, security, and permission constraints, which may never be weakened.

**Amendment procedure**: amendments MUST be recorded in this file with a Sync Impact
Report documenting the version change and the principles or sections affected. Dependent
artifacts — specification, plan, tasks — MUST be re-checked for consistency after any
amendment that changes a principle's substance.

**Versioning policy**: this document follows semantic versioning. MAJOR for a backward
incompatible governance change or the removal or redefinition of a principle; MINOR for a
newly added principle or materially expanded guidance; PATCH for clarifications and
non-semantic refinements.

**Compliance review**: every implementation task MUST be checkable against these
principles. A deviation MUST be justified explicitly in the plan's complexity tracking,
naming the principle deviated from and the reason a simpler compliant alternative was
rejected. An unjustified deviation is a defect.

**Version**: 1.0.0 | **Ratified**: 2026-09-07 | **Last Amended**: 2026-09-07
