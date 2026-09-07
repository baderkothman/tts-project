export type ProviderStatus = 'available' | 'missing_credentials' | 'unreachable';
export type Dialect = 'msa' | 'gulf' | 'egyptian' | 'levantine' | 'maghrebi';
export type Emotion =
  | 'neutral'
  | 'happy'
  | 'excited'
  | 'sad'
  | 'warm'
  | 'calm'
  | 'serious'
  | 'conversational';

export interface ProviderCapabilities {
  streaming: boolean;
  ssml: boolean;
  phoneme: boolean;
  native_emotions: boolean;
  locales: string[];
  formats: string[];
  max_chars: number;
  notes: string;
}

export interface ProviderInfo {
  id: string;
  display_name: string;
  status: ProviderStatus;
  capabilities: ProviderCapabilities;
  voice_count: number;
  unavailable_reason: string | null;
}

export interface VoiceConfig {
  id: string;
  provider: string;
  provider_voice_id: string;
  language: string;
  locale: string;
  dialect: Dialect | null;
  gender: string;
  supports_streaming: boolean;
  supports_emotions: boolean;
  display_name: string;
}

export interface ArabicSample {
  id: string;
  text: string;
  category: string;
  locale: string;
  description: string;
  expected_behavior: string | null;
}

export interface StageDiff {
  stage_name: string;
  before: string;
  after: string;
  changed: boolean;
  duration_ms: number;
}

export interface ProcessedText {
  original: string;
  processed: string;
  stages: StageDiff[];
  changed: boolean;
}

export interface PronunciationDemo {
  original_text: string;
  observed_pronunciation: string;
  desired_pronunciation: string;
  correction_technique: string;
  corrected_text: string;
  provider_observed: string;
  voice_observed: string;
  explanation: string;
}

export interface DialectDetection {
  resolved_dialect: string;
  source: 'user_selected' | 'classifier';
  classifier_label: string | null;
  classifier_confidence: number | null;
  mapped_from_family: boolean;
  unavailable_reason: string | null;
}

export interface DialectComparison {
  original_text: string;
  detection: DialectDetection;
  processed_text: ProcessedText;
  changes: string[];
  raw_audio_ref: string;
  corrected_audio_ref: string;
  architecture_used: string;
}

export interface SynthesisRequest {
  text: string;
  provider: string | null;
  dialect: Dialect | null;
  voice_id: string | null;
  emotion: Emotion;
  client_t0_ms: number;
}

export interface SynthesisResult {
  audio: Blob;
  provider: string | null;
  voice: string | null;
  usedFallback: boolean;
  emotionNative: boolean;
  elapsedMs: number;
}
