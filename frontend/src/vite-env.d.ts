/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** See constants.ts::API_BASE_URL for what this controls. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
