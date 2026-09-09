import { useEffect, useRef, useState } from "react";
import { getPreprocessPreview } from "../api/client";
import type { PipelineMode, PreprocessResponse } from "../types/api";

const DEBOUNCE_MS = 500;

/** Live "what will actually be spoken" preview — debounced so typing
 * doesn't fire a request per keystroke, and cancels a stale in-flight
 * request when the input changes again before it resolves.
 *
 * Local only — never calls the AI dialect rewrite step (OpenAI). That step
 * now runs automatically, but only once, at actual "generate" time (see
 * `dialect_rewriter.py`'s module docstring); typing or changing the dialect
 * here must never trigger a paid API call. This preview can therefore show
 * slightly different wording than what ends up spoken — the real response's
 * `processed_text` (set via `App.tsx`'s `setPreview` after a generation) is
 * what's authoritative for what was actually said. */
export function usePreprocessPreview(text: string, dialectId: string, pipelineMode: PipelineMode) {
  const [preview, setPreview] = useState<PreprocessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!text.trim()) {
      setPreview(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const timer = window.setTimeout(() => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      getPreprocessPreview(text, dialectId, pipelineMode, controller.signal)
        .then((result) => {
          setPreview(result);
          setLoading(false);
        })
        .catch((err) => {
          if (err?.name !== "AbortError") setLoading(false);
        });
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [text, dialectId, pipelineMode]);

  // Exposed so a caller can make this panel authoritative right after a
  // real generation completes — see App.tsx's handleGenerate. Necessary
  // because this hook's own preview and the actual /api/tts call are two
  // independent requests; with the automatic AI dialect rewrite active,
  // each hits a non-deterministic model separately, so they can come back
  // worded differently. Setting it here still comes from the *same* state
  // this hook already owns, so the next real edit's debounced fetch (the
  // effect above) naturally overwrites it again — the override only holds
  // until the user changes something.
  return { preview, loading, setPreview };
}
