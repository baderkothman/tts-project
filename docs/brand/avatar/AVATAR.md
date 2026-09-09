# بيان (Bayan) — لهجتنا's avatar

This is the first real vertical slice of the 15-phase avatar brief, not the
whole thing. It picks one path all the way through — concept → generated
reference art → a working, animated React component → live integration
reacting to real app state — and is honest below about what a single pass
could not responsibly cover. See AGENTS.md §5 ("plan at the right depth")
and §12 ("definition of done... report unrelated or pre-existing
limitations") for why this doc says what it doesn't do, not just what it
does.

## Name and concept

**بيان (Bayan)** — "clear, eloquent expression." Chosen over "صدى" (Echo,
more literal to TTS-as-repetition) and "موج" (Wave, tied to the app's real
waveform visualization) because it reads as a name for a person-like
presence rather than a mechanism — the brief asks for a character, not a
label for the pipeline.

Visual concept: a single rounded, non-robotic silhouette (no limbs, no
joints, no metallic surfaces) with a small brass "radio-dial" mark. That
mark isn't decoration picked in isolation — it deliberately reuses this
app's own existing rationale for the brass accent color
([frontend/DESIGN.md](../../../frontend/DESIGN.md): "brass, radio-dial —
used sparingly"), so Bayan reads as native to لهجتنا's palette rather than
a generic mascot dropped on top of it.

Rejected directions (from the 3 concepts generated): a "modern" and a
"geometric" variant that both added circuit-board line traces across the
body. Circuitry reads as the generic-AI-robot trope the brief explicitly
asked to avoid, so the plain, unornamented "minimalist" concept was kept.

## What exists right now

**Reference concept art** — [bayan-concept-reference.png](bayan-concept-reference.png),
generated via the `design` skill's logo generator (Gemini `nano-banana`,
mascot style). Kept as a reference/mood image only — it is not used as a
production asset. See "Why SVG, not raster" below.

**Production component** — `frontend/src/components/avatar/`:

- `BayanAvatar.tsx` — the SVG itself. Pure, stateless, one `state` prop.
- `types.ts` — `AvatarState`, the entire vocabulary Bayan can be in.
- `useAvatarController.ts` — the finite-state machine (Phase 12's explicit
  requirement: "driven by a finite state machine rather than ad-hoc
  conditionals"). Takes real app booleans in, returns one `AvatarState` out.
- `avatar.css` — the animation set.

**Live integration** — `frontend/src/App.tsx` computes `avatarState` from
real health/loading/error/streaming state and passes it to
`frontend/src/components/Header.tsx`, which renders Bayan (44px) next to
the existing status pill on the app's one current screen. Verified by
running the dev server headlessly and screenshotting all six states
(`sleep`/`error` reachable live since the backend wasn't running during
this pass; `idle`/`thinking`/`talking`/`success` verified via a throwaway
preview harness, not committed).

### The six states this pass covers

| `AvatarState` | Trigger (real app state) | Face |
|---|---|---|
| `sleep` | backend not yet connected, or model still loading | eyes closed (soft arcs), calm mouth |
| `error` | health check failed, or last generation errored | concerned brow, frown |
| `thinking` | a `/api/tts` request is in flight | neutral mouth, eyes glance side to side, brass mark pulses |
| `talking` | streaming synthesis is actively playing | mouth opens/closes on a loop, brass mark pulses |
| `success` | a new result just arrived (transient, ~1.6s) | big smile, one-shot pop animation, then settles to idle |
| `idle` | ready, nothing happening | calm smile, breathing loop, periodic blink |

Priority when several are true at once: `error` > `sleep` > `thinking` >
`talking` > `success` > `idle` — a real problem or a not-ready backend
always outranks a stale "just succeeded" pulse.

### Why SVG, not raster

Phase 3 of the brief itself calls for a "Style D: pure vector, no
gradients, easy to animate" version. Given no billed image-generation
account was available for most of this session (see the gap noted below),
and that breathing/blinking/talking need addressable parts, Bayan was
authored directly as layered SVG rather than drawn once as a PNG and
redrawn as vector later — it's the source of truth, not a stand-in for one.

### Accessibility (Phase 11) — what's actually covered

- **Reduced motion**: no separate code path needed. `frontend/src/index.css`
  already has an app-wide `prefers-reduced-motion: reduce` rule that zeroes
  `animation-duration` and `animation-iteration-count` for every element;
  Bayan's CSS keyframes inherit that automatically.
- **Static fallback**: `<BayanAvatar animated={false} />` renders the pose
  with no CSS animation classes at all, for docs stills or a future
  low-power toggle.
- **Screen readers**: Bayan is `aria-hidden` by default. Every state it
  reflects already has a text equivalent on screen (the status pill, the
  generate button's own loading label, `ErrorBanner`) — giving Bayan its
  own `aria-label` too would double-announce the same fact. A `label` prop
  exists for a future screen where Bayan is the *only* indicator.
- **Not done**: high-contrast mode audit, keyboard-navigation review (Bayan
  isn't interactive yet, so there's nothing to tab to), low-power mode as
  an actual user-facing toggle (only the component-level `animated` escape
  hatch exists).

## What this pass deliberately did not attempt

Executing all 15 phases in one pass was not attempted — several of them
need tooling, accounts, or a product surface this repo doesn't have yet,
and pretending otherwise would misrepresent what was actually verified.
Listed honestly, with the real blocker or reason for each:

- **3D version / GLB model** (Phase 1, 13) — needs a 3D modeling pipeline;
  no such tool is available here. Not started.
- **Rive / Lottie animation exports** (Phase 3, 6, 13) — needs the Rive
  editor or a Lottie-authoring pipeline; the CSS/SVG animation set above
  covers the same *behavior* (breathing, blink, talk, pulse, pop) natively
  in the React app without needing either format. Revisit only if a
  non-web surface (Phase 15's "future mobile app") needs a portable
  animation file.
- **Lip-sync engine across 12 dialects' phonemes** (Phase 7) — real
  phoneme-timed lip sync needs viseme data from the TTS pipeline, which
  `oddadmix/lahgtna-omnivoice-v2` doesn't currently expose. The `talking`
  state's mouth-open loop is a plausible *approximation* tied to real
  playback timing (streaming-active), not phoneme-accurate sync. Building
  the real thing needs a decision about where in the backend pipeline
  viseme/timing data would come from — a backend question, not a frontend
  one, out of scope for this pass.
- **Pose library** (Phase 5: sitting, pointing, presenting, holding a
  phone, etc.) — Bayan's current form is head/face-only by design (a
  chat-bubble-derived silhouette, matching the chosen concept art). Most
  Phase 5 poses assume limbs a bubble-shaped mascot doesn't have. Revisit
  once/if a full-body variant is actually needed by a specific screen.
- **Full UI rollout** (Phase 9) — landing page, dashboard, chat interface,
  voice preview page, onboarding, etc. don't exist in this codebase yet
  (`frontend/src` is currently one screen). Bayan is integrated into that
  one real screen; there is nothing else to integrate into honestly.
- **Figma component library, design tokens export, brand guidelines doc
  beyond this file** (Phase 13) — no Figma file was created this pass.
  Doable on request via the Figma MCP tools already available in this
  environment.
- **Interaction system** (Phase 10: eye tracking on hover, watching the
  keyboard while typing, etc.) — none of this is wired up. The state
  machine above only reacts to backend/generation state, not raw UI
  events, to keep this pass's scope to what could be verified end to end.
- **AI-readiness hooks** (Phase 14: streaming TTS lip-sync, webcam eye
  contact, emotion-from-text, voice-clone previews) — no code for any of
  this exists. The state-machine architecture (typed states in, one
  function computing the state, a pure presentational component) is meant
  to make adding these later a matter of feeding the controller a new
  input, not a redesign — but that's an architectural intention, not a
  verified claim.

## If the next pass continues this

Natural next slice, in order of what's cheapest to verify: (1) a `bust`
size variant for a documentation header, (2) wiring `label` + the button's
own hover/focus state for one real interaction (Phase 10's simplest case),
(3) a Figma file mirroring this SVG via the Figma MCP tools, so design and
code stop being two separate sources of truth for Bayan's shape.
