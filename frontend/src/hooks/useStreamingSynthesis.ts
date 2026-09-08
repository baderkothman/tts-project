import { useCallback, useRef, useState } from "react";
import { base64ToArrayBuffer, synthesizeSpeechStream, type StreamChunkEvent } from "../api/client";
import type { TTSRequestParams } from "../types/api";

export interface StreamingState {
  active: boolean;
  ttfaMs: number | null;
  totalMs: number | null;
  chunkCount: number;
  playedChunks: number;
  error: string | null;
}

const IDLE_STATE: StreamingState = {
  active: false,
  ttfaMs: null,
  totalMs: null,
  chunkCount: 0,
  playedChunks: 0,
  error: null,
};

/** Drives `POST /api/tts/stream` for the UI's "بث تدريجي" demo mode: plays
 * each sentence's audio the moment it arrives via the Web Audio API
 * (gapless — each chunk is scheduled to start exactly when the previous one
 * ends, not on its own arrival time) and reports real, server-measured
 * time-to-first-audio as it happens. This is a demo of the same mechanism
 * `scripts/benchmark_tts.py` measures in `docs/PERFORMANCE_BENCHMARKS.md`,
 * not a production playback engine — see that doc's "what this does and
 * doesn't prove" section for the honest scope. */
export function useStreamingSynthesis() {
  const [state, setState] = useState<StreamingState>(IDLE_STATE);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const nextStartAtRef = useRef(0);
  // Chunks can finish *decoding* out of arrival order (decode time isn't
  // guaranteed to match chunk order) — chaining every chunk's decode+schedule
  // onto the previous one's promise keeps playback strictly sequential
  // regardless of that.
  const scheduleChainRef = useRef<Promise<void>>(Promise.resolve());
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, active: false }));
  }, []);

  const start = useCallback(async (params: TTSRequestParams) => {
    const ctx = audioCtxRef.current ?? new AudioContext();
    audioCtxRef.current = ctx;
    if (ctx.state === "suspended") await ctx.resume();
    nextStartAtRef.current = ctx.currentTime;
    scheduleChainRef.current = Promise.resolve();

    const controller = new AbortController();
    abortRef.current = controller;
    setState({ ...IDLE_STATE, active: true });

    const scheduleChunk = (chunk: StreamChunkEvent) =>
      (async () => {
        const audioBuffer = await ctx.decodeAudioData(base64ToArrayBuffer(chunk.audio_base64));
        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);
        const startAt = Math.max(nextStartAtRef.current, ctx.currentTime);
        source.start(startAt);
        nextStartAtRef.current = startAt + audioBuffer.duration;
      })();

    try {
      const done = await synthesizeSpeechStream(params, {
        signal: controller.signal,
        onChunk: (chunk) => {
          scheduleChainRef.current = scheduleChainRef.current.then(() => scheduleChunk(chunk));
          setState((s) => ({
            ...s,
            ttfaMs: s.ttfaMs ?? chunk.elapsed_ms,
            chunkCount: chunk.chunk_index + 1,
            playedChunks: s.playedChunks + 1,
          }));
        },
      });
      setState((s) => ({ ...s, active: false, totalMs: done.total_ms, ttfaMs: s.ttfaMs ?? done.ttfa_ms }));
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setState((s) => ({ ...s, active: false, error: err instanceof Error ? err.message : "فشل البث التدريجي" }));
    }
  }, []);

  return { state, start, stop };
}
