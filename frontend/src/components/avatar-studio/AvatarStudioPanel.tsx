import { useEffect, useState } from "react";
import { getAvatarEmotions } from "../../api/avatarClient";
import { useAvatarJob } from "../../hooks/useAvatarJob";
import { PITCH_OPTIONS } from "../../constants";
import type { Dialect, Gender, Pitch } from "../../types/api";
import type { EmotionName } from "../../types/avatar";
import { AvatarJobProgress } from "./AvatarJobProgress";
import { AvatarVideoResult } from "./AvatarVideoResult";
import { PortraitUpload } from "./PortraitUpload";

const EMOTION_LABELS: Record<EmotionName, string> = {
  neutral: "محايدة",
  happy: "سعيدة",
  sad: "حزينة",
  excited: "متحمسة",
  calm: "هادئة",
  professional: "احترافية",
};

const PITCH_LABELS: Record<Pitch, string> = {
  "very low pitch": "منخفضة جدًا",
  "low pitch": "منخفضة",
  "moderate pitch": "متوسطة",
  "high pitch": "عالية",
  "very high pitch": "عالية جدًا",
};

// Fallback in case /api/tts/avatar/emotions hasn't resolved yet — mirrors
// backend/app/data/emotions.py's EMOTION_NAMES order. The real list is
// still fetched (see useEffect below) so a future preset addition on the
// server shows up here without a frontend deploy.
const FALLBACK_EMOTIONS: EmotionName[] = ["neutral", "happy", "sad", "excited", "calm", "professional"];

export function AvatarStudioPanel({
  dialects,
  modelReady,
  aiRewriteAvailable,
}: {
  dialects: Dialect[];
  modelReady: boolean;
  aiRewriteAvailable: boolean;
}) {
  const [text, setText] = useState("");
  const [dialectId, setDialectId] = useState("msa");
  const [gender, setGender] = useState<Gender | null>("female");
  const [pitch, setPitch] = useState<Pitch>("moderate pitch");
  const [emotion, setEmotion] = useState<EmotionName>("neutral");
  const [portrait, setPortrait] = useState<File | null>(null);
  const [emotions, setEmotions] = useState<EmotionName[]>(FALLBACK_EMOTIONS);
  const [aiDialectRewrite, setAiDialectRewrite] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { job, creating, error, create, cancel, reset } = useAvatarJob();

  useEffect(() => {
    getAvatarEmotions()
      .then((res) => setEmotions(res.emotions))
      .catch(() => setEmotions(FALLBACK_EMOTIONS));
  }, []);

  const busy = creating || (job !== null && !["completed", "failed", "cancelled"].includes(job.status));

  function handleGenerate() {
    if (!text.trim()) {
      setFormError("اكتب نصًا أولًا");
      return;
    }
    if (!portrait) {
      setFormError("ارفع صورة شخصية أولًا");
      return;
    }
    setFormError(null);
    void create({ text, dialectId, gender, pitch, emotion, portrait, aiDialectRewrite });
  }

  return (
    <main className="composer-card">
      <section className="composer-col composer-col--workspace">
        <div className="field">
          <label className="composer__label" htmlFor="avatar-text">
            النص
          </label>
          <textarea
            id="avatar-text"
            className="composer__textarea"
            dir="auto"
            rows={5}
            placeholder="اكتب النص الذي سيقوله الصورة الناطقة…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
          />
        </div>

        <PortraitUpload file={portrait} onFileChange={setPortrait} />

        {formError && <p className="field__error">{formError}</p>}
        {error && <div className="error-banner">{error}</div>}

        {!job && (
          <div className="actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleGenerate}
              disabled={creating || !modelReady || !text.trim() || !portrait}
            >
              {creating ? (
                <>
                  <LoadingBars /> جارٍ البدء…
                </>
              ) : (
                "ولّد الصورة الناطقة"
              )}
            </button>
          </div>
        )}

        {job && !["completed", "failed", "cancelled"].includes(job.status) && (
          <AvatarJobProgress job={job} onCancel={cancel} />
        )}
        {job && job.status === "failed" && <AvatarJobProgress job={job} onCancel={cancel} />}
        {job && job.status === "cancelled" && (
          <>
            <AvatarJobProgress job={job} onCancel={cancel} />
            <div className="actions">
              <button type="button" className="btn btn--ghost" onClick={reset}>
                حاول مجددًا
              </button>
            </div>
          </>
        )}
        {job && job.status === "completed" && <AvatarVideoResult job={job} onRegenerate={reset} />}
      </section>

      <section className="composer-col composer-col--settings">
        <div className="field">
          <span className="field__label">اللهجة</span>
          <div className="dialect-rail" role="radiogroup" aria-label="اختيار اللهجة">
            {dialects.map((d) => (
              <button
                key={d.id}
                type="button"
                role="radio"
                aria-checked={d.id === dialectId}
                className={`dialect-chip${d.id === dialectId ? " dialect-chip--active" : ""}`}
                onClick={() => setDialectId(d.id)}
                disabled={busy}
                title={d.name_en}
              >
                {d.name_ar}
              </button>
            ))}
          </div>

          <label
            className="checkbox-row"
            title={aiRewriteAvailable ? undefined : "يتطلب إعداد OPENAI_API_KEY على الخادم"}
          >
            <input
              type="checkbox"
              checked={aiDialectRewrite}
              disabled={!aiRewriteAvailable || busy}
              onChange={(e) => setAiDialectRewrite(e.target.checked)}
            />
            إعادة صياغة باللهجة عبر OpenAI (تشكيل تلقائي)
          </label>
          {aiDialectRewrite && aiRewriteAvailable && (
            <p className="field__hint">
              سيُرسل النص المكتوب إلى OpenAI لإعادة صياغته وتشكيله حسب اللهجة المختارة قبل توليد
              الصوت والفيديو.
            </p>
          )}
          {!aiRewriteAvailable && (
            <p className="field__hint">غير متاحة على هذا الخادم — يتطلب إعداد OPENAI_API_KEY.</p>
          )}
        </div>

        <div className="field">
          <span className="field__label">الصوت</span>
          <div className="voice-design">
            <div className="voice-design__row">
              <span className="voice-design__label">الجنس</span>
              <div className="pill-group">
                {(["female", "male"] as Gender[]).map((g) => (
                  <button
                    key={g}
                    type="button"
                    className={`pill${gender === g ? " pill--active" : ""}`}
                    onClick={() => setGender(gender === g ? null : g)}
                    disabled={busy}
                  >
                    {g === "female" ? "أنثى" : "ذكر"}
                  </button>
                ))}
                <button
                  type="button"
                  className={`pill${gender === null ? " pill--active" : ""}`}
                  onClick={() => setGender(null)}
                  disabled={busy}
                >
                  تلقائي
                </button>
              </div>
            </div>

            <div className="voice-design__row">
              <span className="voice-design__label">
                درجة الصوت <em className="voice-design__value">{PITCH_LABELS[pitch]}</em>
              </span>
              <input
                type="range"
                className="range"
                min={0}
                max={PITCH_OPTIONS.length - 1}
                value={PITCH_OPTIONS.indexOf(pitch)}
                onChange={(e) => setPitch(PITCH_OPTIONS[Number(e.target.value)])}
                aria-valuetext={PITCH_LABELS[pitch]}
                disabled={busy}
              />
            </div>
          </div>
        </div>

        <div className="field">
          <label className="field__label" htmlFor="avatar-emotion">
            التعبير
          </label>
          <select
            id="avatar-emotion"
            className="select"
            value={emotion}
            onChange={(e) => setEmotion(e.target.value as EmotionName)}
            disabled={busy}
          >
            {emotions.map((name) => (
              <option key={name} value={name}>
                {EMOTION_LABELS[name] ?? name}
              </option>
            ))}
          </select>
          <p className="field__hint">
            يؤثر التعبير على شدة الحركة وابتسامة الوجه دون كسر تزامن الشفاه — انظر
            docs/AVATAR_ARCHITECTURE.md لتفاصيل ما يدعمه المحرّك الحالي فعليًا.
          </p>
        </div>
      </section>
    </main>
  );
}

function LoadingBars() {
  return (
    <span className="loading-bars" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </span>
  );
}
