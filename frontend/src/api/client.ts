import type { Dialect, HealthResponse, ModelInfo, TTSRequestParams, TTSResponse, VoiceOptions } from "../types/api";

// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts). In
// production the frontend build is served by FastAPI itself from the same
// origin, so a relative path works unchanged in both.
const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (body.detail?.message) return body.detail.message;
    return res.statusText || "حدث خطأ غير متوقع";
  } catch {
    return res.statusText || "حدث خطأ غير متوقع";
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function getModelInfo(): Promise<ModelInfo> {
  const res = await fetch(`${BASE}/model-info`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function getDialects(): Promise<Dialect[]> {
  const res = await fetch(`${BASE}/dialects`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function getVoiceOptions(): Promise<VoiceOptions> {
  const res = await fetch(`${BASE}/voices`);
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

export async function synthesizeSpeech(params: TTSRequestParams): Promise<TTSResponse> {
  const form = new FormData();
  form.set("text", params.text);
  form.set("mode", params.mode);
  form.set("dialect_id", params.dialect_id);
  if (params.gender) form.set("gender", params.gender);
  form.set("pitch", params.pitch);
  if (params.age) form.set("age", params.age);
  form.set("whisper", String(params.whisper));
  if (params.ref_text) form.set("ref_text", params.ref_text);
  form.set("speed", String(params.speed));
  form.set("quality", params.quality);
  form.set("guidance_scale", String(params.guidance_scale));
  if (params.ref_audio) form.set("ref_audio", params.ref_audio);

  const res = await fetch(`${BASE}/tts`, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

/** Decodes a base64 audio payload into a plain ArrayBuffer — used both to
 * build the playable Blob and to feed the waveform decoder. */
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const buffer = new ArrayBuffer(binary.length);
  const view = new Uint8Array(buffer);
  for (let i = 0; i < binary.length; i++) view[i] = binary.charCodeAt(i);
  return buffer;
}
