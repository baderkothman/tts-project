// Mirrors backend/app/models/tts.py and backend/app/data/*.py. Kept by hand
// in sync with the Python source of truth — there is no shared schema
// generation step in this prototype.

export type Gender = "male" | "female";
export type Pitch = "very low pitch" | "low pitch" | "moderate pitch" | "high pitch" | "very high pitch";
export type AgeGroup = "child" | "teenager" | "young adult" | "middle-aged" | "elderly";
export type Quality = "fast" | "high";
export type Mode = "voice_design" | "clone" | "auto";

export interface Dialect {
  id: string;
  name_en: string;
  name_ar: string;
  language_code: string | null;
  written_only: boolean;
}

export interface VoiceOptions {
  supports_named_voices: boolean;
  supports_voice_design: boolean;
  supports_voice_cloning: boolean;
  gender_options: Gender[];
  pitch_options: Pitch[];
  age_options: AgeGroup[];
  note: string;
}

export interface ModelCapabilities {
  voice_design: boolean;
  voice_cloning: boolean;
  dialect_control: boolean;
  diacritics_aware: boolean;
  named_voice_roster: boolean;
}

export interface ModelInfo {
  repo_id: string;
  architecture: string;
  base_model: string;
  device: string;
  sample_rate: number;
  dialects_supported: number;
  capabilities: ModelCapabilities;
}

export interface HealthResponse {
  status: "ok" | "loading" | "error";
  model_loaded: boolean;
  device?: string | null;
  detail?: string | null;
}

export interface LatencyInfo {
  generation_ms: number;
  audio_duration_ms: number;
  real_time_factor: number;
}

export interface TTSResponse {
  audio_base64: string;
  content_type: string;
  sample_rate: number;
  mode: Mode;
  dialect_id: string | null;
  gender: Gender | null;
  latency: LatencyInfo;
  warnings: string[];
}

export interface TTSRequestParams {
  text: string;
  mode: Mode;
  dialect_id: string;
  gender: Gender | null;
  pitch: Pitch;
  age: AgeGroup | null;
  whisper: boolean;
  ref_text: string | null;
  speed: number;
  quality: Quality;
  guidance_scale: number;
  ref_audio: File | null;
}
