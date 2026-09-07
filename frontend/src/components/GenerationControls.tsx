import type { Quality } from "../types/api";

export function GenerationControls({
  speed,
  onSpeedChange,
  quality,
  onQualityChange,
}: {
  speed: number;
  onSpeedChange: (v: number) => void;
  quality: Quality;
  onQualityChange: (q: Quality) => void;
}) {
  return (
    <details className="disclosure">
      <summary>إعدادات التوليد</summary>
      <div className="voice-design__row">
        <span className="voice-design__label">
          السرعة <em className="voice-design__value ltr-num">{speed.toFixed(2)}×</em>
        </span>
        <input
          type="range"
          className="range"
          min={0.5}
          max={2}
          step={0.05}
          value={speed}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
        />
      </div>
      <div className="voice-design__row">
        <span className="voice-design__label">الجودة</span>
        <div className="pill-group">
          <button
            type="button"
            className={`pill${quality === "high" ? " pill--active" : ""}`}
            onClick={() => onQualityChange("high")}
          >
            جودة عالية
          </button>
          <button
            type="button"
            className={`pill${quality === "fast" ? " pill--active" : ""}`}
            onClick={() => onQualityChange("fast")}
          >
            أسرع
          </button>
        </div>
      </div>
    </details>
  );
}
