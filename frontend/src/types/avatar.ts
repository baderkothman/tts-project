// Mirrors backend/app/models/avatar.py and backend/app/data/emotions.py.
// Same "kept in sync by hand, no schema-generation step" note as types/api.ts.

export type EmotionName = "neutral" | "happy" | "sad" | "excited" | "calm" | "professional";

export type AvatarJobStatus =
  | "queued"
  | "preprocessing"
  | "generating_audio"
  | "preparing_avatar"
  | "generating_video"
  | "encoding"
  | "completed"
  | "failed"
  | "cancelled";

export const TERMINAL_STATUSES: readonly AvatarJobStatus[] = ["completed", "failed", "cancelled"];

export interface AvatarJobResponse {
  job_id: string;
  status: AvatarJobStatus;
  progress: number;
  engine: string | null;
  audio_url: string | null;
  video_url: string | null;
  duration: number | null;
  processing_time: number | null;
  error_kind: string | null;
  error: string | null;
  warnings: string[];
  created_at: number;
  updated_at: number;
}

export interface AvatarJobEvent {
  job_id: string;
  status: AvatarJobStatus;
  progress: number;
}

export interface EmotionsResponse {
  emotions: EmotionName[];
  default: EmotionName;
}
