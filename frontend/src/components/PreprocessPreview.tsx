import type { PreprocessResponse } from "../types/api";

const LANGUAGE_LABELS: Record<"ar" | "en", string> = { ar: "عربي", en: "إنجليزي" };

export function PreprocessPreview({
  preview,
  loading,
}: {
  preview: PreprocessResponse | null;
  loading: boolean;
}) {
  if (!preview && !loading) return null;

  return (
    <details className="disclosure preview">
      <summary>
        معاينة النص المنطوق
        {loading && <span className="preview__loading-dot" aria-hidden="true" />}
      </summary>

      {preview && (
        <div className="preview__body">
          <div className="preview__block">
            <span className="preview__label">النص الأصلي</span>
            <p className="preview__text" dir="auto">
              {preview.original_text}
            </p>
          </div>

          <div className="preview__block">
            <span className="preview__label">النص الجاهز للنطق</span>
            <p className="preview__text preview__text--processed" dir="rtl">
              {preview.processed_text}
            </p>
          </div>

          {preview.segments.length > 1 && (
            <div className="preview__block">
              <span className="preview__label">المقاطع المكتشفة</span>
              <ul className="preview__segments">
                {preview.segments.map((seg, i) => (
                  <li key={i} className={`preview__segment preview__segment--${seg.language}`}>
                    <span className="preview__segment-tag">{LANGUAGE_LABELS[seg.language]}</span>
                    <span dir="auto">{seg.speak_text.trim() || "…"}</span>
                    {seg.diacritized && <span className="preview__segment-badge">مُشكَّل</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {preview.warnings.length > 0 && (
            <ul className="preview__warnings">
              {preview.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </details>
  );
}
