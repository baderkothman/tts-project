// Mirrors backend/app/models/tts.py and backend/app/data/*.py. Kept by hand
// in sync with the Python source of truth — there is no shared schema
// generation step in this prototype.

export type Gender = "male" | "female";
export type Pitch = "very low pitch" | "low pitch" | "moderate pitch" | "high pitch" | "very high pitch";
export type Quality = "fast" | "high";
export type Mode = "voice_design" | "clone" | "auto";
export type PipelineMode = "native" | "dual_model" | "transliteration";

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
  note: string;
}

export interface ModelCapabilities {
  voice_design: boolean;
  voice_cloning: boolean;
  dialect_control: boolean;
  diacritics_aware: boolean;
  named_voice_roster: boolean;
  automatic_diacritization: boolean;
  mixed_language_support: boolean;
}

export interface ModelInfo {
  repo_id: string;
  architecture: string;
  base_model: string;
  device: string;
  sample_rate: number;
  dialects_supported: number;
  capabilities: ModelCapabilities;
  pipeline_modes: PipelineMode[];
  diacritizer_loaded: boolean;
  english_tts_loaded: boolean;
  dialect_rewriter_configured: boolean;
}

export interface SegmentInfo {
  language: "ar" | "en";
  original_text: string;
  speak_text: string;
  diacritized: boolean;
}

export interface PreprocessResponse {
  original_text: string;
  processed_text: string;
  segments: SegmentInfo[];
  warnings: string[];
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
  pipeline_mode: PipelineMode;
  dialect_id: string | null;
  gender: Gender | null;
  latency: LatencyInfo;
  processed_text: string;
  segments: SegmentInfo[];
  warnings: string[];
}

export interface TTSRequestParams {
  text: string;
  mode: Mode;
  pipeline_mode: PipelineMode;
  dialect_id: string;
  gender: Gender | null;
  pitch: Pitch;
  whisper: boolean;
  ref_text: string | null;
  speed: number;
  quality: Quality;
  guidance_scale: number;
  ref_audio: File | null;
  ai_dialect_rewrite: boolean;
}
