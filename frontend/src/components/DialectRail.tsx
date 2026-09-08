import type { Dialect } from "../types/api";

export function DialectRail({
  dialects,
  selectedId,
  onSelect,
  aiRewrite,
  onAiRewriteChange,
  aiRewriteAvailable,
}: {
  dialects: Dialect[];
  selectedId: string;
  onSelect: (id: string) => void;
  aiRewrite: boolean;
  onAiRewriteChange: (enabled: boolean) => void;
  aiRewriteAvailable: boolean;
}) {
  return (
    <div className="field">
      <span className="field__label">اللهجة</span>
      <div className="dialect-rail" role="radiogroup" aria-label="اختيار اللهجة">
        {dialects.map((d) => (
          <button
            key={d.id}
            type="button"
            role="radio"
            aria-checked={d.id === selectedId}
            className={`dialect-chip${d.id === selectedId ? " dialect-chip--active" : ""}`}
            onClick={() => onSelect(d.id)}
            title={d.written_only ? `${d.name_en} — تُنقل عبر النص المكتوب فقط` : d.name_en}
          >
            {d.name_ar}
            {d.written_only && <span className="dialect-chip__mark">•</span>}
          </button>
        ))}
      </div>
      {dialects.find((d) => d.id === selectedId)?.written_only && (
        <p className="field__hint">
          هذه اللهجة لا تملك مُعامل نموذج مستقل بعد — يعتمد نطقها على العامية التي تكتبها في
          النص نفسه.
        </p>
      )}

      <label className="checkbox-row" title={aiRewriteAvailable ? undefined : "يتطلب إعداد OPENAI_API_KEY على الخادم"}>
        <input
          type="checkbox"
          checked={aiRewrite}
          disabled={!aiRewriteAvailable}
          onChange={(e) => onAiRewriteChange(e.target.checked)}
        />
        إعادة صياغة باللهجة عبر OpenAI (تشكيل تلقائي)
      </label>
      {aiRewrite && aiRewriteAvailable && (
        <p className="field__hint">
          سيُرسل النص المكتوب إلى OpenAI لإعادة صياغته وتشكيله حسب اللهجة المختارة قبل
          التوليد. أي كلمات إنجليزية تبقى كما هي دون ترجمة أو تحويل إلى حروف عربية.
        </p>
      )}
      {!aiRewriteAvailable && (
        <p className="field__hint">غير متاحة على هذا الخادم — يتطلب إعداد OPENAI_API_KEY.</p>
      )}
    </div>
  );
}
