import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { cancelAvatarJob, createAvatarJob, getAvatarJob, subscribeToAvatarJob, type AvatarGenerationParams } from "../api/avatarClient";
import type { AvatarJobResponse } from "../types/avatar";
import { TERMINAL_STATUSES } from "../types/avatar";

export interface AvatarJobHookState {
  job: AvatarJobResponse | null;
  creating: boolean;
  error: string | null;
}

/** Drives one avatar job end to end: create -> subscribe to its SSE
 * progress stream -> one final full-shape fetch once it reaches a terminal
 * status (the stream itself only carries `{status, progress}` — see
 * `subscribeToAvatarJob`'s doc — the terminal fetch is what actually
 * populates `video_url`/`audio_url`/`duration`/etc). Mirrors
 * `useStreamingSynthesis.ts`'s shape (state + start + stop) for the
 * existing streaming demo, adapted for a job that outlives one request. */
export function useAvatarJob() {
  const [state, setState] = useState<AvatarJobHookState>({ job: null, creating: false, error: null });
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const stopSubscription = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
  }, []);

  useEffect(() => stopSubscription, [stopSubscription]);

  const create = useCallback(
    async (params: AvatarGenerationParams) => {
      stopSubscription();
      setState({ job: null, creating: true, error: null });
      try {
        const { job_id } = await createAvatarJob(params);
        const initial = await getAvatarJob(job_id);
        setState({ job: initial, creating: false, error: null });

        unsubscribeRef.current = subscribeToAvatarJob(job_id, {
          onEvent: (event) => {
            setState((s) => (s.job ? { ...s, job: { ...s.job, status: event.status, progress: event.progress } } : s));
            if (TERMINAL_STATUSES.includes(event.status)) {
              stopSubscription();
              // The stream's own event is status+progress only — fetch the
              // full shape once so video_url/audio_url/duration/error are
              // actually populated.
              getAvatarJob(job_id)
                .then((full) => setState((s) => ({ ...s, job: full })))
                .catch(() => {
                  /* the terminal status from the stream itself already
                   * reached the UI; a failed follow-up fetch just means a
                   * stale media/duration display, not a stuck spinner. */
                });
            }
          },
        });
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "تعذّر بدء توليد الصورة الناطقة";
        setState({ job: null, creating: false, error: message });
      }
    },
    [stopSubscription],
  );

  const cancel = useCallback(async () => {
    if (!state.job) return;
    try {
      await cancelAvatarJob(state.job.job_id);
    } catch {
      // The next SSE event (or the terminal fetch) reflects real state
      // regardless — a failed cancel *request* isn't itself shown as an
      // error, since the job may already have finished on its own.
    }
  }, [state.job]);

  const reset = useCallback(() => {
    stopSubscription();
    setState({ job: null, creating: false, error: null });
  }, [stopSubscription]);

  return { ...state, create, cancel, reset };
}
