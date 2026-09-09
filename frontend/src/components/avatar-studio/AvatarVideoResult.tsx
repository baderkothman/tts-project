import type { AvatarJobResponse } from "../../types/avatar";

export function AvatarVideoResult({ job, onRegenerate }: { job: AvatarJobResponse; onRegenerate: () => void }) {
  if (!job.video_url) return null;

  return (
    <div className="avatar-result">
      <video className="avatar-result__video" src={job.video_url} controls playsInline />

      <div className="avatar-result__meta">
        {job.duration != null && (
          <span>
            المدة: <span className="ltr-num">{job.duration.toFixed(1)}s</span>
          </span>
        )}
        {job.processing_time != null && (
          <span>
            وقت المعالجة: <span className="ltr-num">{job.processing_time.toFixed(1)}s</span>
          </span>
        )}
        {job.engine && (
          <span>
            المحرّك: <span className="ltr-num">{job.engine}</span>
          </span>
        )}
      </div>

      {job.warnings.length > 0 && (
        <ul className="preview__warnings">
          {job.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      <div className="actions">
        <a className="btn btn--primary" href={job.video_url} download={`avatar-${job.job_id}.mp4`}>
          تنزيل الفيديو (MP4)
        </a>
        {job.audio_url && (
          <a className="btn btn--ghost" href={job.audio_url} download={`avatar-${job.job_id}.wav`}>
            تنزيل الصوت (WAV)
          </a>
        )}
        <button type="button" className="btn btn--ghost" onClick={onRegenerate}>
          إعادة التوليد
        </button>
      </div>
    </div>
  );
}
