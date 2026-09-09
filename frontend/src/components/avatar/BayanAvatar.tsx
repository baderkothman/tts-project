import type { AvatarState } from "./types";
import "./avatar.css";

const MOUTH_PATH: Record<Exclude<AvatarState, "talking">, string> = {
  idle: "M48,74 Q60,82 72,74",
  sleep: "M50,75 Q60,79 70,75",
  thinking: "M50,76 Q60,78 70,76",
  success: "M46,71 Q60,89 74,71",
  error: "M48,79 Q60,71 72,79",
};

export interface BayanAvatarProps {
  state: AvatarState;
  /** Pixel size of the square viewport the SVG scales into. */
  size?: number;
  /** Set false to render a static pose with no CSS animations — for
   * documentation stills, low-power mode, or a screen already dense with
   * motion. `prefers-reduced-motion` is handled globally (see index.css)
   * and needs no extra prop here. */
  animated?: boolean;
  /** Only pass a label where Bayan is the *sole* indicator of a state —
   * everywhere in this app a text status already says the same thing
   * (StatusPill, the generate button's own label, ErrorBanner), so the
   * default is decorative/`aria-hidden` to avoid double-announcing the
   * same information to screen readers. */
  label?: string;
  className?: string;
}

/** بيان — Bayan, لهجتنا's avatar. A single rounded, non-robotic form with a
 * small brass "radio-dial" mark (echoing this app's own brass = radio-dial
 * accent rationale, see frontend/DESIGN.md) rather than a face bolted onto
 * generic AI-assistant iconography. Renders one of `AvatarState`'s six
 * poses — see useAvatarController for how real app state maps onto them,
 * and docs/brand/avatar/AVATAR.md for the full design rationale and the
 * expressions/poses intentionally left for a later pass. */
export function BayanAvatar({ state, size = 56, animated = true, label, className }: BayanAvatarProps) {
  const asleep = state === "sleep";
  const talking = state === "talking";
  const cls = (...parts: (string | false | undefined)[]) => parts.filter(Boolean).join(" ");

  return (
    <svg
      viewBox="0 0 120 132"
      width={size}
      height={size}
      className={cls("bayan", `bayan--${state}`, animated && "bayan--animated", className)}
      role={label ? "img" : undefined}
      aria-hidden={label ? undefined : true}
    >
      {label && <title>{label}</title>}

      <g className="bayan__breathe">
        {/* tail */}
        <path
          className="bayan__tail"
          d="M32,86 C28,96 24,104 26,114 C33,108 40,100 44,90 Z"
          fill="var(--teal, #1f5e5b)"
        />

        {/* body */}
        <rect x="12" y="8" width="96" height="84" rx="34" ry="34" fill="var(--teal, #1f5e5b)" />

        {/* brass radio-dial mark */}
        <g className="bayan__mark" transform="translate(33,28)">
          <circle r="7" fill="none" stroke="var(--brass, #84602a)" strokeWidth="3" />
          <circle r="2.6" fill="var(--brass, #84602a)" />
          <path
            d="M-13,-9 A18,18 0 0 1 -3,-17"
            fill="none"
            stroke="var(--brass, #84602a)"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </g>

        {/* eyes */}
        {asleep ? (
          <g className="bayan__eyes-closed" stroke="var(--surface-raised, #fffdf7)" strokeWidth="3.5" strokeLinecap="round">
            <path d="M38,54 Q44,58 50,54" fill="none" />
            <path d="M70,54 Q76,58 82,54" fill="none" />
          </g>
        ) : (
          <g className="bayan__eyes">
            <g className="bayan__eye">
              <circle cx="44" cy="52" r="10" fill="var(--surface-raised, #fffdf7)" />
              <circle className="bayan__pupil" cx="44" cy="52" r="4.4" fill="var(--teal-deep, #163f3d)" />
            </g>
            <g className="bayan__eye bayan__eye--right">
              <circle cx="76" cy="52" r="10" fill="var(--surface-raised, #fffdf7)" />
              <circle className="bayan__pupil" cx="76" cy="52" r="4.4" fill="var(--teal-deep, #163f3d)" />
            </g>
          </g>
        )}

        {/* eyebrows — only the "concerned" state needs them */}
        {state === "error" && (
          <g stroke="var(--surface-raised, #fffdf7)" strokeWidth="3" strokeLinecap="round">
            <path d="M37,38 L51,42" fill="none" />
            <path d="M83,38 L69,42" fill="none" />
          </g>
        )}

        {/* mouth */}
        {talking ? (
          <ellipse className="bayan__mouth-talk" cx="60" cy="75" rx="7" ry="5" fill="var(--surface-raised, #fffdf7)" />
        ) : (
          <path
            className="bayan__mouth"
            d={MOUTH_PATH[state]}
            fill="none"
            stroke="var(--surface-raised, #fffdf7)"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
        )}
      </g>
    </svg>
  );
}
