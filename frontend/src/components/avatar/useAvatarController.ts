import { useEffect, useRef, useState } from "react";
import type { AvatarState } from "./types";

const SUCCESS_HOLD_MS = 1600;

export interface AvatarControllerInput {
  /** Backend reachable and reported at least once. */
  connected: boolean;
  /** Model failed health check, or the last generation request errored. */
  hasError: boolean;
  /** Model is still loading for the first time. */
  modelLoading: boolean;
  /** A /api/tts request is in flight. */
  generating: boolean;
  /** Streaming synthesis is actively scheduling/playing audio. */
  streamingActive: boolean;
  /** Identity of the most recent successful result — any change is treated
   * as "a new result just arrived" and triggers the transient success pulse.
   * `null` before anything has been generated. */
  resultToken: string | null;
}

/** Bayan's state machine. Deterministic, one direction of truth: app state
 * in, `AvatarState` out. No component reaches in and sets an expression
 * directly — see AGENTS.md's "state explicit and inspectable" rule and
 * Phase 12 of the avatar brief (finite state machine, not ad-hoc
 * conditionals).
 *
 * Priority order (highest first): error > sleep > thinking > talking >
 * success (transient) > idle. A real problem or a not-ready backend always
 * outranks a stale "just succeeded" pulse. */
export function useAvatarController(input: AvatarControllerInput): AvatarState {
  const { connected, hasError, modelLoading, generating, streamingActive, resultToken } = input;

  const [successPulse, setSuccessPulse] = useState(false);
  const lastResultToken = useRef<string | null>(null);
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (resultToken === null || resultToken === lastResultToken.current) return;
    lastResultToken.current = resultToken;
    setSuccessPulse(true);
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setSuccessPulse(false), SUCCESS_HOLD_MS);
    return () => window.clearTimeout(timerRef.current);
  }, [resultToken]);

  if (hasError) return "error";
  if (!connected || modelLoading) return "sleep";
  if (generating) return "thinking";
  if (streamingActive) return "talking";
  if (successPulse) return "success";
  return "idle";
}
