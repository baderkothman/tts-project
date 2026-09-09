import type { AvatarJobResponse, AvatarJobStatus } from "../../types/avatar";

const STEPS: { labels: string[]; statuses: AvatarJobStatus[] }[] = [
  { labels: ["تجهيز النص العربي"], statuses: ["queued", "preprocessing"] },
  { labels: ["توليد الصوت"], statuses: ["generating_audio"] },
  { labels: ["تحريك الصورة"], statuses: ["preparing_avatar", "generating_video"] },
  { labels: ["ترميز الفيديو"], statuses: ["encoding", "completed"] },
];

function stepIndexFor(status: AvatarJobStatus): number {
  const i = STEPS.findIndex((s) => s.statuses.includes(status));
  return i === -1 ? 0 : i;
}

const ERROR_KIND_LABELS: Record<string, string> = {
  invalid_input: "المدخلات غير صالحة لهذا الطلب.",
  generation_failed: "تعذّر توليد الفيديو.",
  not_available: "خدمة توليد الفيديو غير متاحة حاليًا على هذا الخادم.",
  timeout: "استغرق التوليد وقتًا أطول من الحد المسموح.",
  internal_error: "حدث خطأ غير متوقع أثناء التوليد.",
};

export function AvatarJobProgress({ job, onCancel }: { job: AvatarJobResponse; onCancel: () => void }) {
  if (job.status === "failed") {
    return (
      <div className="error-banner">
        <span>{ERROR_KIND_LABELS[job.error_kind ?? ""] ?? job.error ?? "فشل توليد الصورة الناطقة."}</span>
      </div>
    );
  }
  if (job.status === "cancelled") {
    return <p className="field__hint">تم إلغاء توليد الصورة الناطقة.</p>;
  }

  const activeStep = stepIndexFor(job.status);

  return (
    <div className="avatar-progress">
      <p className="avatar-progress__title">جارٍ توليد الصورة الناطقة…</p>
      <ul className="avatar-progress__steps">
        {STEPS.map((step, i) => (
          <li
            key={step.labels[0]}
            className={`avatar-progress__step${i < activeStep ? " avatar-progress__step--done" : i === activeStep ? " avatar-progress__step--active" : ""}`}
          >
            <span className="avatar-progress__marker" aria-hidden="true">
              {i < activeStep ? "✓" : i === activeStep ? "●" : "○"}
            </span>
            {step.labels[0]}
          </li>
        ))}
      </ul>

      <div className="avatar-progress__bar" role="progressbar" aria-valuenow={job.progress} aria-valuemin={0} aria-valuemax={100}>
        <div className="avatar-progress__bar-fill" style={{ width: `${job.progress}%` }} />
      </div>
      <span className="avatar-progress__percent ltr-num">{job.progress}%</span>

      <button type="button" className="btn btn--ghost" onClick={onCancel}>
        إلغاء
      </button>
    </div>
  );
}
