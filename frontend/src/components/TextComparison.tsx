import type { ProcessedText } from '../types';

interface TextComparisonProps {
  result: ProcessedText | null;
}

export function TextComparison({ result }: TextComparisonProps) {
  if (!result) {
    return (
      <div className="empty-state">
        <span className="empty-state__mark" aria-hidden="true">أ → أَ</span>
        <p>عاين النص لترى أثر كل مرحلة من مراحل المعالجة.</p>
      </div>
    );
  }

  const changedStages = result.stages.filter((stage) => stage.changed);
  return (
    <div className="comparison" aria-live="polite">
      <div className="comparison__text">
        <div>
          <span className="eyebrow">قبل المعالجة</span>
          <p>{result.original}</p>
        </div>
        <div className="comparison__processed">
          <span className="eyebrow">جاهز للنطق</span>
          <p>{result.processed}</p>
        </div>
      </div>
      <div className="stage-list" aria-label="مراحل المعالجة التي غيّرت النص">
        {changedStages.length ? (
          changedStages.map((stage) => (
            <span className="stage-chip" key={stage.stage_name}>
              {stage.stage_name}
              <b dir="ltr">{stage.duration_ms.toFixed(1)} ms</b>
            </span>
          ))
        ) : (
          <span className="stage-chip stage-chip--quiet">لم يحتج النص إلى تعديل</span>
        )}
      </div>
    </div>
  );
}
