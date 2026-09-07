import type { AgeGroup, Gender, Mode, Pitch } from "../types/api";
import { PITCH_OPTIONS } from "../constants";
import { ReferenceAudioUpload } from "./ReferenceAudioUpload";

interface VoicePanelProps {
  mode: Mode;
  onModeChange: (m: Mode) => void;
  gender: Gender | null;
  onGenderChange: (g: Gender | null) => void;
  pitch: Pitch;
  onPitchChange: (p: Pitch) => void;
  age: AgeGroup | null;
  onAgeChange: (a: AgeGroup | null) => void;
  whisper: boolean;
  onWhisperChange: (w: boolean) => void;
  refAudio: File | null;
  onRefAudioChange: (f: File | null) => void;
  refText: string;
  onRefTextChange: (t: string) => void;
}

const AGE_LABELS: Record<AgeGroup, string> = {
  child: "طفل",
  teenager: "مراهق",
  "young adult": "شاب",
  "middle-aged": "متوسط العمر",
  elderly: "مسن",
};

const PITCH_LABELS: Record<Pitch, string> = {
  "very low pitch": "منخفضة جدًا",
  "low pitch": "منخفضة",
  "moderate pitch": "متوسطة",
  "high pitch": "عالية",
  "very high pitch": "عالية جدًا",
};

export function VoicePanel(props: VoicePanelProps) {
  const { mode, onModeChange } = props;

  return (
    <div className="field">
      <div className="segmented" role="tablist" aria-label="طريقة الصوت">
        <button
          type="button"
          role="tab"
          aria-selected={mode !== "clone"}
          className={`segmented__option${mode !== "clone" ? " segmented__option--active" : ""}`}
          onClick={() => onModeChange("voice_design")}
        >
          تصميم الصوت
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "clone"}
          className={`segmented__option${mode === "clone" ? " segmented__option--active" : ""}`}
          onClick={() => onModeChange("clone")}
        >
          استنساخ من عيّنة
        </button>
      </div>

      {mode === "clone" ? (
        <ReferenceAudioUpload
          file={props.refAudio}
          onFileChange={props.onRefAudioChange}
          refText={props.refText}
          onRefTextChange={props.onRefTextChange}
        />
      ) : (
        <div className="voice-design">
          <div className="voice-design__row">
            <span className="voice-design__label">الجنس</span>
            <div className="pill-group">
              {(["female", "male"] as Gender[]).map((g) => (
                <button
                  key={g}
                  type="button"
                  className={`pill${props.gender === g ? " pill--active" : ""}`}
                  onClick={() => props.onGenderChange(props.gender === g ? null : g)}
                >
                  {g === "female" ? "أنثى" : "ذكر"}
                </button>
              ))}
              <button
                type="button"
                className={`pill${props.gender === null ? " pill--active" : ""}`}
                onClick={() => props.onGenderChange(null)}
              >
                تلقائي
              </button>
            </div>
          </div>

          <div className="voice-design__row">
            <span className="voice-design__label">
              درجة الصوت <em className="voice-design__value">{PITCH_LABELS[props.pitch]}</em>
            </span>
            <input
              type="range"
              className="range"
              min={0}
              max={PITCH_OPTIONS.length - 1}
              value={PITCH_OPTIONS.indexOf(props.pitch)}
              onChange={(e) => props.onPitchChange(PITCH_OPTIONS[Number(e.target.value)])}
              aria-valuetext={PITCH_LABELS[props.pitch]}
            />
          </div>

          <details className="disclosure">
            <summary>خيارات إضافية</summary>
            <div className="voice-design__row">
              <span className="voice-design__label">الفئة العمرية</span>
              <select
                className="select"
                value={props.age ?? ""}
                onChange={(e) => props.onAgeChange((e.target.value || null) as AgeGroup | null)}
              >
                <option value="">بدون تفضيل</option>
                {(Object.keys(AGE_LABELS) as AgeGroup[]).map((a) => (
                  <option key={a} value={a}>
                    {AGE_LABELS[a]}
                  </option>
                ))}
              </select>
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={props.whisper}
                onChange={(e) => props.onWhisperChange(e.target.checked)}
              />
              نبرة همس (whisper)
            </label>
          </details>
        </div>
      )}
    </div>
  );
}
