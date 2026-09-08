import type {
  Dialect,
  Gender,
  HealthResponse,
  ModelInfo,
  PipelineMode,
  PreprocessResponse,
  TTSRequestParams,
  TTSResponse,
  VoiceOptions,
} from "../types/api";

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

export async function getPreprocessPreview(
  text: string,
  dialect_id: string,
  pipeline_mode: PipelineMode,
  ai_dialect_rewrite: boolean,
  gender: Gender | null,
  signal?: AbortSignal,
): Promise<PreprocessResponse> {
  const res = await fetch(`${BASE}/preprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, dialect_id, pipeline_mode, ai_dialect_rewrite, gender }),
    signal,
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

function buildTtsForm(params: TTSRequestParams): FormData {
  const form = new FormData();
  form.set("text", params.text);
  form.set("mode", params.mode);
  form.set("pipeline_mode", params.pipeline_mode);
  form.set("dialect_id", params.dialect_id);
  if (params.gender) form.set("gender", params.gender);
  form.set("pitch", params.pitch);
  form.set("whisper", String(params.whisper));
  if (params.ref_text) form.set("ref_text", params.ref_text);
  form.set("speed", String(params.speed));
  form.set("quality", params.quality);
  form.set("guidance_scale", String(params.guidance_scale));
  if (params.ref_audio) form.set("ref_audio", params.ref_audio);
  form.set("ai_dialect_rewrite", String(params.ai_dialect_rewrite));
  return form;
}

export async function synthesizeSpeech(params: TTSRequestParams): Promise<TTSResponse> {
  const res = await fetch(`${BASE}/tts`, { method: "POST", body: buildTtsForm(params) });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  return res.json();
}

/** One sentence-chunk of audio from `POST /api/tts/stream` — see
 * `backend/app/api/tts.py`'s `_stream_events` for the server side. */
export interface StreamChunkEvent {
  chunk_index: number;
  chunk_text: string;
  audio_base64: string;
  content_type: string;
  sample_rate: number;
  audio_duration_ms: number;
  /** Milliseconds since the request started — chunk 0's value is the
   * time-to-first-audio measurement the streaming endpoint exists for. */
  elapsed_ms: number;
  is_final: boolean;
  warnings: string[];
}

export interface StreamDoneEvent {
  chunk_count: number;
  ttfa_ms: number | null;
  total_ms: number;
  total_audio_duration_ms: number;
  real_time_factor: number;
  warnings: string[];
}

function parseSseBlock(block: string): { type: string; data: unknown } | null {
  let type = "message";
  let dataLine: string | null = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) type = line.slice("event: ".length);
    else if (line.startsWith("data: ")) dataLine = line.slice("data: ".length);
  }
  if (dataLine === null) return null;
  return { type, data: JSON.parse(dataLine) };
}

/** Consumes the sentence-chunked SSE stream from `POST /api/tts/stream`,
 * invoking `onChunk` as each sentence's audio arrives, and resolving with
 * the closing `done` event's aggregate stats once the stream ends. */
export async function synthesizeSpeechStream(
  params: TTSRequestParams,
  { onChunk, signal }: { onChunk: (chunk: StreamChunkEvent) => void; signal?: AbortSignal },
): Promise<StreamDoneEvent> {
  const res = await fetch(`${BASE}/tts/stream`, { method: "POST", body: buildTtsForm(params), signal });
  if (!res.ok) throw new ApiError(res.status, await parseErrorDetail(res));
  if (!res.body) throw new ApiError(0, "المتصفح لا يدعم قراءة الاستجابة كتيار بيانات");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let done: StreamDoneEvent | null = null;

  while (true) {
    const { value, done: streamEnded } = await reader.read();
    if (streamEnded) break;
    buffer += decoder.decode(value, { stream: true });
    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const event = parseSseBlock(block);
      if (!event) continue;
      if (event.type === "chunk") onChunk(event.data as StreamChunkEvent);
      else if (event.type === "done") done = event.data as StreamDoneEvent;
      else if (event.type === "error") {
        const detail = event.data as { message?: string };
        throw new ApiError(502, detail.message ?? "فشل التوليد التدريجي");
      }
    }
  }
  if (!done) throw new ApiError(0, "انقطع البث قبل اكتماله");
  return done;
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
