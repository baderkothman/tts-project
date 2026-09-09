import { useEffect, useRef, useState } from "react";

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ["image/png", "image/jpeg", "image/webp"];

export function PortraitUpload({ file, onFileChange }: { file: File | null; onFileChange: (f: File | null) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function accept(candidate: File) {
    if (candidate.size > MAX_BYTES) {
      setLocalError("حجم الصورة يتجاوز 8 ميغابايت");
      return;
    }
    if (candidate.type && !ACCEPTED.includes(candidate.type)) {
      setLocalError("صيغة غير مدعومة — استخدم PNG أو JPEG أو WebP");
      return;
    }
    setLocalError(null);
    onFileChange(candidate);
  }

  return (
    <div className="field">
      <span className="field__label">الصورة الشخصية</span>
      <div
        className={`dropzone dropzone--portrait${dragging ? " dropzone--active" : ""}`}
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
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) accept(f);
          }}
        />
        {file && previewUrl ? (
          <div className="dropzone__portrait-preview">
            <img src={previewUrl} alt="معاينة الصورة الشخصية" />
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
          </div>
        ) : (
          <>
            <p>اسحب صورة شخصية هنا أو اضغط للاختيار</p>
            <p className="dropzone__hint">وجه واحد واضح، بدون انسداد كبير — PNG أو JPEG أو WebP، حتى 8 ميغابايت</p>
          </>
        )}
      </div>
      {localError && <p className="field__error">{localError}</p>}
    </div>
  );
}
