import { useRef, useState } from "react";

const MAX_BYTES = 15 * 1024 * 1024;
const ACCEPTED = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/flac", "audio/ogg", "audio/webm"];

export function ReferenceAudioUpload({
  file,
  onFileChange,
  refText,
  onRefTextChange,
}: {
  file: File | null;
  onFileChange: (f: File | null) => void;
  refText: string;
  onRefTextChange: (t: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function accept(candidate: File) {
    if (candidate.size > MAX_BYTES) {
      setLocalError("حجم الملف يتجاوز 15 ميغابايت");
      return;
    }
    if (candidate.type && !ACCEPTED.includes(candidate.type)) {
      setLocalError("صيغة غير مدعومة — استخدم WAV أو MP3 أو FLAC أو OGG");
      return;
    }
    setLocalError(null);
    onFileChange(candidate);
  }

  return (
    <div className="voice-design">
      <div
        className={`dropzone${dragging ? " dropzone--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) accept(f);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) accept(f);
          }}
        />
        {file ? (
          <div className="dropzone__file">
            <strong>{file.name}</strong>
            <span className="ltr-num">{(file.size / (1024 * 1024)).toFixed(1)} MB</span>
            <button
              type="button"
              className="dropzone__remove"
              onClick={(e) => {
                e.stopPropagation();
                onFileChange(null);
              }}
            >
              إزالة
            </button>
          </div>
        ) : (
          <>
            <p>اسحب عيّنة صوتية هنا أو اضغط للاختيار</p>
            <p className="dropzone__hint">عيّنة من 3 إلى 10 ثوانٍ تعطي أفضل نتيجة — WAV أو MP3 أو FLAC أو OGG</p>
          </>
        )}
      </div>
      {localError && <p className="field__error">{localError}</p>}

      <div className="voice-design__row">
        <label htmlFor="ref-text" className="voice-design__label">
          نص العيّنة (اختياري)
        </label>
        <input
          id="ref-text"
          className="text-input"
          dir="auto"
          placeholder="اتركه فارغًا ليُفرَّغ صوتيًا تلقائيًا"
          value={refText}
          onChange={(e) => onRefTextChange(e.target.value)}
        />
      </div>
    </div>
  );
}
