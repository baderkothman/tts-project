import type { Pitch } from "./types/api";

// The backend's origin, with no trailing slash — "" (the default) means
// every request stays a relative "/api/..." path, correct for local dev
// (vite.config.ts's own proxy) and for the single-container mode where
// FastAPI serves this build itself from the same origin
// (backend/app/main.py's StaticFiles mount). Set VITE_API_BASE_URL at
// *build* time (see frontend/Dockerfile) only when this frontend is
// deployed as its own service, separate from the backend — Vite inlines
// `import.meta.env.*` into the bundle at build time; there is no runtime
// env var to read once this is a static SPA. A trailing slash is stripped
// defensively so `${API_BASE_URL}/api` never ends up with "//api".
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

// Mirrors backend/app/data/voice_design.py::PITCH_OPTIONS verbatim (order matters).
export const PITCH_OPTIONS: Pitch[] = [
  "very low pitch",
  "low pitch",
  "moderate pitch",
  "high pitch",
  "very high pitch",
];
