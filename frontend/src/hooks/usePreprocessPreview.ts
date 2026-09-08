import { useEffect, useRef, useState } from "react";
import { getPreprocessPreview } from "../api/client";
import type { PipelineMode, PreprocessResponse } from "../types/api";

const DEBOUNCE_MS = 500;

/** Live "what will actually be spoken" preview — debounced so typing
 * doesn't fire a request per keystroke, and cancels a stale in-flight
 * request when the input changes again before it resolves. */
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

  return { preview, loading };
}
