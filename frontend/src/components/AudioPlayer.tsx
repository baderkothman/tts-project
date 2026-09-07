import { useEffect, useRef, useState } from "react";
import { useWaveformPeaks } from "../hooks/useWaveformPeaks";
import { formatDuration, formatMs } from "../utils/format";
import type { Dialect, TTSResponse } from "../types/api";

export function AudioPlayer({
  result,
  audioUrl,
  arrayBuffer,
  dialect,
  fileNameHint,
}: {
  result: TTSResponse;
  audioUrl: string;
  arrayBuffer: ArrayBuffer;
  dialect: Dialect | null;
  fileNameHint: string;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const peaks = useWaveformPeaks(arrayBuffer);

  useEffect(() => {
    setPlaying(false);
    setCurrentTime(0);
  }, [audioUrl]);

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (el.paused) {
      void el.play();
    } else {
      el.pause();
    }
  }

  function replay() {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = 0;
    void el.play();
  }

  function seekTo(fraction: number) {
    const el = audioRef.current;
    if (!el || !duration) return;
    el.currentTime = fraction * duration;
  }

  const progress = duration > 0 ? currentTime / duration : 0;

  return (
    <div className="player">
      <audio
        ref={audioRef}
        src={audioUrl}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
      />

      <div className="player__controls">
        <button type="button" className="player__play" onClick={togglePlay} aria-label={playing ? "إيقاف مؤقت" : "تشغيل"}>
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>

        <Waveform peaks={peaks} progress={progress} onSeek={seekTo} />

        <span className="player__time ltr-num">
          {formatDuration(currentTime)} / {formatDuration(duration)}
        </span>

        <button type="button" className="player__icon-btn" onClick={replay} aria-label="إعادة من البداية" title="إعادة">
          <ReplayIcon />
        </button>

        <a
          className="player__icon-btn"
          href={audioUrl}
          download={`${fileNameHint}.wav`}
          aria-label="تنزيل الملف الصوتي"
          title="تنزيل"
        >
          <DownloadIcon />
        </a>
      </div>

      <div className="player__meta">
        {dialect && <span>{dialect.name_ar}</span>}
        {result.gender && <span>{result.gender === "female" ? "أنثى" : "ذكر"}</span>}
        <span className="ltr-num">RTF {result.latency.real_time_factor.toFixed(2)}</span>
        <span className="ltr-num">{formatMs(result.latency.generation_ms)}</span>
      </div>

      {result.warnings.length > 0 && (
        <ul className="player__warnings">
          {result.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Waveform({
  peaks,
  progress,
  onSeek,
}: {
  peaks: number[] | null;
  progress: number;
  onSeek: (fraction: number) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);

  function handleClick(e: React.MouseEvent) {
    const el = trackRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    onSeek(Math.min(1, Math.max(0, fraction)));
  }

  return (
    <div className="waveform" ref={trackRef} onClick={handleClick} role="slider" aria-label="موضع التشغيل" aria-valuenow={Math.round(progress * 100)}>
      {peaks ? (
        peaks.map((p, i) => {
          const barProgress = i / peaks.length;
          return (
            <span
              key={i}
              className={`waveform__bar${barProgress <= progress ? " waveform__bar--played" : ""}`}
              style={{ height: `${Math.max(8, p * 100)}%` }}
            />
          );
        })
      ) : (
        <span className="waveform__loading" />
      )}
      <span className="waveform__cursor" style={{ insetInlineStart: `${progress * 100}%` }} />
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
    </svg>
  );
}
function ReplayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
      <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" />
    </svg>
  );
}
function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
      <path d="M5 20h14v-2H5v2zM13 12V4h-2v8H8l4 4 4-4h-3z" />
    </svg>
  );
}
