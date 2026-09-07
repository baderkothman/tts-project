const MAX_CHARS = 2000;

export function TextComposer({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const count = value.length;
  const over = count > MAX_CHARS;

  return (
    <div className="composer">
      <label htmlFor="tts-text" className="composer__label">
        النص
      </label>
      <textarea
        id="tts-text"
        className="composer__textarea"
        dir="rtl"
        placeholder="اكتب نصك هنا… جرّب: «إيش أخبارك اليوم؟» أو «عامل إيه؟» أو «كيفك اليوم؟»"
        value={value}
        maxLength={MAX_CHARS + 200}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
      />
      <div className="composer__meta">
        <span className={`composer__count ltr-num${over ? " composer__count--over" : ""}`}>
          {count} / {MAX_CHARS}
        </span>
      </div>
    </div>
  );
}
