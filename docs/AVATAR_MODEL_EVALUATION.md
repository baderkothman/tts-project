# Talking Avatar model evaluation

This is a **desk evaluation** — repository/license/hardware research done directly
against each candidate's current source, not live-benchmarked side by side in this
environment. The reason is stated plainly rather than glossed over: see [Hardware
reality](#hardware-reality-the-decisive-constraint) below. Where a claim is unverified,
it's marked as such rather than presented as measured.

## Models evaluated

| Model | Org | Repo | License | Audio-driven? | Real VRAM/hardware requirement (sourced) | Apple Silicon signal |
|---|---|---|---|---|---|---|
| [LivePortrait](https://github.com/KwaiVGI/LivePortrait) | Kuaishou (KwaiVGI) | github.com/KwaiVGI/LivePortrait | permissive (see repo) | **No** — video-driven face reenactment/retargeting, not audio-driven. Needs a driving video or a separate audio→motion module in front of it | Light, ~6–12GB VRAM | Only candidate with a real community macOS/Apple-Silicon port (`Lytanshade/LivePortrait-pinokio`: "Nvidia and MacOS silicon supported") |
| [MuseTalk](https://github.com/TMElyralab/MuseTalk) | Tencent (TMElyralab) | github.com/TMElyralab/MuseTalk | Apache-2.0 | Yes — mouth-region-only lip sync composited onto an existing video/portrait, real-time capable (30fps+ on a Tesla V100) | 4–12GB VRAM (CUDA); even the lightest documented case (RTX 3050 Ti, fp16) takes ~5 min for an 8s clip | None found |
| [LatentSync](https://github.com/bytedance/LatentSync) | ByteDance | github.com/bytedance/LatentSync | Apache-2.0 | Yes — Stable-Diffusion-based lip sync | 6.5–18GB VRAM depending on version (1.5 ≈8GB, 1.6 ≈18GB); `diffusers`/CUDA-oriented | None found |
| [EchoMimicV2](https://github.com/antgroup/echomimic_v2) | Ant Group / Alipay | github.com/antgroup/echomimic_v2 | Apache-2.0 (family) | Yes — semi-body human animation, video-diffusion-based | Not independently published for V2; the sibling V3 model documents 12GB+; CUDA-only architecture | None found |
| [Hallo2](https://github.com/fudan-generative-vision/hallo2) | Fudan / Baidu / Nanjing Univ. | github.com/fudan-generative-vision/hallo2 | **Mixed** — base repo is open, but its high-resolution/CodeFormer component is licensed **S-Lab License 1.0** (non-commercial-leaning) | Yes | 16–24GB VRAM recommended (10–12GB explicitly documented as "below recommended") | None found |
| [SadTalker](https://github.com/OpenTalker/SadTalker) | OpenTalker | github.com/OpenTalker/SadTalker | Apache-2.0 (license was updated, non-commercial restriction removed) | Yes | Moderate; 2023-era architecture, visibly behind the diffusion-based options on realism | Occasional unverified community CPU/MPS forks; no credible signal |
| [FantasyTalking](https://github.com/Fantasy-AMAP/fantasy-talking) | Alibaba (Fantasy-AMAP) | github.com/Fantasy-AMAP/fantasy-talking | Apache-2.0 | Yes | Built on **Wan2.1-I2V-14B** — a 14B-parameter video diffusion foundation model. Even its cheapest documented config: 5GB VRAM but ~42.6s *per denoising step*, with a full clip needing ~20–50 steps | None; needs datacenter-class GPU |

Sources are the repositories/model cards linked above, checked directly during this
evaluation (2026-09-09), not recalled from training data. Where a number has a range,
it's the range the source itself gives, not an estimate.

## Hardware reality: the decisive constraint

This app's actual development/deployment hardware for this pass:

```
Darwin, Apple M5 — torch.cuda.is_available() == False, torch.backends.mps.is_available() == True
```

Every genuinely **audio-driven** candidate above (MuseTalk, LatentSync, EchoMimicV2,
Hallo2, SadTalker, FantasyTalking) is built and benchmarked exclusively against CUDA —
none has a credible, verified Apple Silicon/MPS execution path. The one candidate with
real Apple Silicon support (LivePortrait) is not audio-driven at all — it reenacts a
*driving video's* motion, not audio.

This is the same category of hardware mismatch this repo already navigated for its core
TTS model (`oddadmix/lahgtna-omnivoice-v2` runs on MPS today — see `README.md` and
`backend/app/services/inference.py`'s CUDA→MPS→CPU device selection) — the difference is
that no candidate avatar model here has an MPS path at all, working or otherwise, so
there is no "just run it slower" option the way there was for TTS.

**Consequence:** live-benchmarking all seven locally, as a literal reading of "benchmark
them specifically for this application" would require, was not attempted — it would mean
either downloading multi-GB weights for models with no realistic path to running on this
hardware, or fabricating numbers for hardware that was never actually exercised. Neither
is acceptable. See `docs/AVATAR_ARCHITECTURE.md` for what was built instead
(`StubAvatarEngine`, a real, audio-reactive, non-AI placeholder verified end-to-end) and
the concrete plan for the real engine (`avatar_engines/hf_jobs_engine.py`'s module
docstring — dispatching MuseTalk as a remote Hugging Face Job, since this repo already
has `HF_TOKEN` configured and already depends on the HF Hub).

## Combining specialized models?

The brief asks whether an audio→lip-sync→portrait-animation→stabilization pipeline beats
one model doing everything. Genuinely worth doing eventually: **MuseTalk (mouth-region
lip sync) driving a base video, with LivePortrait-style techniques adding head
motion/blink on top** is a real, sourced combination — MuseTalk's own documentation is
explicit that it only modifies the mouth region of an existing video, so *something* else
has to supply head movement, blinking, and idle motion regardless of which lip-sync model
is chosen. This is architecturally identical to what `docs/PRODUCTION_ARCHITECTURE.md`
(§5, written before this feature existed) already recommended for lip-sync in a real-time
avatar context: start with amplitude-envelope-driven mouth movement (cheap, no extra
model), only add forced-phoneme/model-driven lip sync if visual fidelity demands it.
`StubAvatarEngine` *is* that tier-1 approach, built for real rather than only described.

Not tested locally for the reason above — this is a sourced architectural judgment, not a
benchmarked result, and is flagged as such.

## Final recommendation — updated after real verification

**Originally recommended MuseTalk** for the reasons below (kept for the record — the
underlying research is still accurate), but MuseTalk (and LatentSync/EchoMimicV2) turned
out to have a disqualifying practical problem discovered only by trying to actually use
one: **all three lip-sync an *existing video*, not a single still photo.** This app's
input is one portrait image, not a driving video — using any of them would first require
generating a synthetic "talking-ish" video from the photo (exactly the gap
`StubAvatarEngine` fills) and *then* running a second lip-sync pass over it, real added
complexity the brief's own architecture section only asks for "if testing demonstrates a
meaningful improvement." SadTalker's own description — "audio-driven **single image**
talking face animation" — is the one candidate actually built for this app's real input
shape, not an artifact of research; this was re-confirmed directly against Replicate's
live schema for it (`required: ["source_image", "driven_audio"]`, both single files, no
video input at all).

**Active now: `ReplicateAvatarEngine` running SadTalker via Replicate's hosted API**
(`backend/app/services/avatar_engines/replicate_engine.py`) — chosen over self-hosting per
the Hardware reality section above, and **verified for real**, twice: once as a raw API
call (a synthetic photorealistic test portrait, a 2s test tone, a real downloaded MP4 with
visibly moving lips across frames), and once through this app's own real UI end to end
(real Arabic TTS audio from this app's own `SpeechPipeline`, a real portrait upload, a
real generated video with genuinely moving lips synced to that audio — `engine:
"replicate:sadtalker"`, `processing_time: ~71s`, no fabricated numbers). Real, metered
cost: ~$0.09–0.15 per generation, confirmed against actual billed predictions.

Falls back to `StubAvatarEngine` automatically when `REPLICATE_API_TOKEN` isn't set (see
`main.py::_select_avatar_engine`) — the free, non-AI placeholder is still real and still
tested, just no longer the primary path when a Replicate credential is configured.

**Original MuseTalk reasoning, for a future "combine specialized models" pass:** if a
richer engine than SadTalker is worth building later (SadTalker is a 2023-era
architecture, visibly behind the newer diffusion-based options on realism), the right
shape is *not* "swap SadTalker for MuseTalk" but "run SadTalker (or `StubAvatarEngine`)
for a base talking-ish video, then MuseTalk for mouth-region refinement" — MuseTalk is
real-time-capable (30fps+ on a V100), Apache-2.0, and mouth-region-only by design, so it
composes with a first pass rather than replacing it. Not attempted this round — SadTalker
alone already clears the bar of "real AI lip sync, working, verified."

**Still not selected, with the disqualifying reason for each (updated):**

- **MuseTalk, LatentSync, EchoMimicV2** — require an existing video input, not a single
  photo (see above) — a real architecture mismatch with this app's input shape, discovered
  by checking the actual input schema, not assumed from the model name.
- **FantasyTalking** — 14B-parameter foundation model, tens of seconds per denoising step;
  disproportionate cost/latency for this use case regardless of the video-input question.
- **Hallo2** — license risk (S-Lab 1.0 on its HR path) disqualifies it outright per the
  brief's own "License suitability: Critical" weighting.
- **LivePortrait** — not audio-driven at all; still a real candidate for a future
  head-motion layer, not for the core lip-sync slot.
