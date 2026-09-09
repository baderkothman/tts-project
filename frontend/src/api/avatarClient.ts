import { ApiError } from "./client";
import type { AvatarJobEvent, AvatarJobResponse, EmotionName, EmotionsResponse } from "../types/avatar";
import type { Gender, Pitch } from "../types/api";

const BASE = "/api/tts/avatar";

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    return res.statusText || "حدث خطأ غير متوقع";
  } catch {
    return res.statusText || "حدث خطأ غير متوقع";
  }
}

export interface AvatarGenerationParams {
  text: string;
  dialectId: string;
  gender: Gender | null;
  pitch: Pitch;
  emotion: EmotionName;
  portrait: File;
}

export async function getAvatarEmotions(): Promise<EmotionsResponse> {
  const res = await fetch(`${BASE}/emotions`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function createAvatarJob(params: AvatarGenerationParams): Promise<{ job_id: string; status: string }> {
  const form = new FormData();
  form.set("text", params.text);
  form.set("mode", "voice_design");
  form.set("dialect_id", params.dialectId);
  if (params.gender) form.set("gender", params.gender);
  form.set("pitch", params.pitch);
  form.set("emotion", params.emotion);
  form.set("portrait", params.portrait);

  const res = await fetch(BASE, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function getAvatarJob(jobId: string): Promise<AvatarJobResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function cancelAvatarJob(jobId: string): Promise<{ cancelled: boolean }> {
  const res = await fetch(`${BASE}/jobs/${jobId}/cancel`, { method: "POST" });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

/** Opens the SSE progress stream for one job. `EventSource` (not the
 * `fetch`+manual-parse approach `synthesizeSpeechStream` in client.ts
 * uses for /api/tts/stream) is a deliberate difference, not an
 * inconsistency: that endpoint is a POST carrying a request body (fetch is
 * the only option), while this one is a plain GET the browser's own
 * `EventSource` handles natively, including automatic reconnect — which a
 * long-running job's progress stream benefits from and a one-shot audio
 * stream doesn't need. Returns a cleanup function; the caller is
 * responsible for calling it (on unmount or once a terminal status
 * arrives). */
export function subscribeToAvatarJob(
  jobId: string,
  { onEvent, onError }: { onEvent: (event: AvatarJobEvent) => void; onError?: () => void },
): () => void {
  const source = new EventSource(`${BASE}/jobs/${jobId}/events`);
  source.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data) as AvatarJobEvent);
    } catch {
      // A malformed event is dropped rather than crashing the stream —
      // the next polling-equivalent GET (or the next event) recovers.
    }
  };
  source.onerror = () => onError?.();
  return () => source.close();
}
