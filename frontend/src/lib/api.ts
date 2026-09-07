import type {
  ArabicSample,
  DialectComparison,
  ProcessedText,
  PronunciationDemo,
  ProviderInfo,
  SynthesisRequest,
  SynthesisResult,
  VoiceConfig,
} from '../types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function errorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) return fallback;
  const detail = payload.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String(detail.message);
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => (typeof item === 'object' && item && 'msg' in item ? item.msg : item)).join('، ');
  }
  return fallback;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(errorMessage(payload, response.statusText), response.status);
  }
  return response.json() as Promise<T>;
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  providers: () => requestJson<ProviderInfo[]>('/api/providers'),
  voices: (provider: string, signal?: AbortSignal) =>
    requestJson<VoiceConfig[]>(`/api/voices?provider=${encodeURIComponent(provider)}`, { signal }),
  samples: () => requestJson<ArabicSample[]>('/api/samples'),
  preview: (request: SynthesisRequest) => requestJson<ProcessedText>('/api/preview', jsonPost(request)),
  pronunciationDemo: () => requestJson<PronunciationDemo>('/api/pronunciation/demo'),
  compareDialect: (text: string, dialect: string | null) =>
    requestJson<DialectComparison>('/api/dialect/compare', jsonPost({ text, dialect })),
  async synthesize(request: SynthesisRequest): Promise<SynthesisResult> {
    const startedAt = performance.now();
    const response = await fetch('/api/tts/stream', jsonPost(request));
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new ApiError(errorMessage(payload, response.statusText), response.status);
    }
    return {
      audio: await response.blob(),
      provider: response.headers.get('X-TTS-Provider'),
      voice: response.headers.get('X-TTS-Voice'),
      usedFallback: response.headers.get('X-TTS-Used-Fallback') === 'true',
      emotionNative: response.headers.get('X-TTS-Emotion-Native') === 'true',
      elapsedMs: performance.now() - startedAt,
    };
  },
};

export function audioFromBase64(value: string, mime = 'audio/mpeg'): Blob {
  const binary = atob(value);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new Blob([bytes], { type: mime });
}
