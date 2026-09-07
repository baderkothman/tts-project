# Design notes — لهجتنا

Produced with the `frontend-design` skill's process (plan → critique against generic-AI
defaults → build). Kept here so a future pass has the reasoning, not just the CSS.

## Subject

An Arabic dialect TTS tool. The real content is: 13 real dialects across the Arab world, a
gender/pitch/age voice-design vocabulary, and a generated waveform. The design should make
the dialect choice feel like the primary, tactile decision it is — not a buried `<select>`
in a settings panel.

## Rejected defaults

Checked against the common AI-generated-page tells before building:

- Cream (#F4F1EA) + terracotta accent — the most common "AI page" palette right now, and
  specifically Claude's own interaction color. Rejected.
- Near-black + neon accent — rejected.
- Cairo/Tajawal for Arabic type — both are themselves the default reach for "an Arabic
  website" and would read as templated for this specific brief.
- ALL-CAPS eyebrows, middle-dot-joined meta strings, arrow-suffixed buttons — none used.

## Tokens

- **Color** — warm stone paper (`#EDE7D8`) instead of cream; deep teal (`#1F5E5B`,
  evoking Gulf/Red Sea water — a real geographic anchor for an Arabic-dialect product, and
  not a color that shows up in the generic-AI palette survey) as the primary accent; brass
  (`#B8863B`, radio-dial) as a sparing secondary, used only for the "written-only dialect"
  marker and warnings; clay (`#A8402F`) for errors. Full dark-mode token set via
  `prefers-color-scheme`.
- **Type** — two families, clearly distinct roles per the skill's guidance: **Noto Naskh
  Arabic** for the wordmark/display (real calligraphic warmth, not a generic UI grotesque)
  and **IBM Plex Sans Arabic** (+ IBM Plex Sans for Latin/numeral fragments like `MPS`,
  `RTF 0.96`) for everything functional. Neither is the default reach for "an Arabic app."
- **Layout** — single centered column (`760px`), RTL-native. The dialect rail is a wrapped
  row of pill chips, not a dropdown — it's the one bold, non-quiet element in the page, per
  the skill's "spend your boldness in one place" principle. Everything else (panels,
  sliders, the audio player) stays flat and quiet: hairline borders, one soft shadow tier,
  no gradients, no per-card drop shadows.

## One real, non-decorative touch

The audio player's waveform is not a static asset or randomized bar pattern — it's
computed client-side from the actual decoded PCM samples of the audio that came back
(`src/hooks/useWaveformPeaks.ts`), downsampled to ~96 peak buckets. It's real information
(you're looking at the actual clip), not decoration standing in for it.

## Things tried and reverted

- A three-way "· "-joined status string (`النموذج جاهز · MPS · v0.3`) — cut down to
  status + device only; a third joined fragment started reading like the generic
  middle-dot-metadata tell even though each piece was real.
- `guidance_scale` as a visible slider — real and documented, but a fourth slider on the
  primary flow started crowding the "advanced" disclosure without adding much perceptible
  value over its sensible default; left backend-only for now.
