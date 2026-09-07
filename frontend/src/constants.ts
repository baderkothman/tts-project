import type { Pitch } from "./types/api";

// Mirrors backend/app/data/voice_design.py::PITCH_OPTIONS verbatim (order matters).
export const PITCH_OPTIONS: Pitch[] = [
  "very low pitch",
  "low pitch",
  "moderate pitch",
  "high pitch",
  "very high pitch",
];
