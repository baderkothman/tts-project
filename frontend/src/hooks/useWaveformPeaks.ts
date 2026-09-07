import { useEffect, useState } from "react";

/** Decodes real audio data into ~N peak buckets for the waveform display —
 * not decorative noise, an actual (if low-resolution) picture of the clip. */
export function useWaveformPeaks(arrayBuffer: ArrayBuffer | null, buckets = 96): number[] | null {
  const [peaks, setPeaks] = useState<number[] | null>(null);

  useEffect(() => {
    if (!arrayBuffer) {
      setPeaks(null);
      return;
    }
    let cancelled = false;
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();

    ctx
      .decodeAudioData(arrayBuffer.slice(0))
      .then((buffer) => {
        if (cancelled) return;
        const data = buffer.getChannelData(0);
        const bucketSize = Math.max(1, Math.floor(data.length / buckets));
        const result: number[] = [];
        for (let i = 0; i < buckets; i++) {
          const start = i * bucketSize;
          const end = Math.min(start + bucketSize, data.length);
          let peak = 0;
          for (let j = start; j < end; j++) {
            const abs = Math.abs(data[j]);
            if (abs > peak) peak = abs;
          }
          result.push(peak);
        }
        const max = Math.max(...result, 0.01);
        setPeaks(result.map((v) => v / max));
      })
      .catch(() => {
        if (!cancelled) setPeaks(null);
      })
      .finally(() => {
        void ctx.close();
      });

    return () => {
      cancelled = true;
    };
  }, [arrayBuffer, buckets]);

  return peaks;
}
