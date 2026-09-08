import type { StreamingState } from "../hooks/useStreamingSynthesis";

/** Demonstrates `POST /api/tts/stream` (sentence-chunked audio, played
 * gapless via Web Audio as each chunk arrives) as an alternative to the
 * main "ولّد الصوت" button, surfacing the same time-to-first-audio number
 * `scripts/benchmark_tts.py` measures in `docs/PERFORMANCE_BENCHMARKS.md` —
 * live, for this exact text, instead of only in a report. */
export function StreamingDemo({
  state,
  onToggle,
  disabled,
}: {
  state: StreamingState;
  onToggle: () => void;
  disabled: boolean;
}) {
  const hasResult = state.ttfaMs !== null && !state.active;

  return (
    <div className="streaming-demo">
      <button type="button" className="btn btn--ghost" onClick={onToggle} disabled={disabled && !state.active}>
        {state.active ? "إيقاف البث" : "تجربة البث التدريجي (قياس زمن أول صوت)"}
      </button>

      {(state.active || hasResult || state.error) && (
        <p className="streaming-demo__status">
          {state.error && <span className="field__error">{state.error}</span>}

          {!state.error && state.active && (
            <>
              يبث الآن — قطعة <span className="ltr-num" dir="ltr">{state.playedChunks}</span>
              {state.ttfaMs !== null && (
                <>
                  {" "}
                  — أول صوت خلال <span className="ltr-num" dir="ltr">{Math.round(state.ttfaMs)}ms</span>
                </>
              )}
            </>
          )}

          {!state.error && hasResult && (
            <>
              اكتمل — <span className="ltr-num" dir="ltr">{state.chunkCount}</span> قطع، أول صوت خلال{" "}
              <span className="ltr-num" dir="ltr">{Math.round(state.ttfaMs ?? 0)}ms</span>، الإجمالي{" "}
              <span className="ltr-num" dir="ltr">{Math.round(state.totalMs ?? 0)}ms</span>
            </>
          )}
        </p>
      )}
    </div>
  );
}
