import type { Dialect } from "../types/api";

export function DialectRail({
  dialects,
  selectedId,
  onSelect,
}: {
  dialects: Dialect[];
  selectedId: string;
  onSelect: (id: string) => void;
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
    </div>
  );
}
