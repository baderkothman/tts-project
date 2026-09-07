import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { PronunciationDemo } from '../types';
import { SparkIcon } from './Icons';

export function PronunciationLab() {
  const [demo, setDemo] = useState<PronunciationDemo | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.pronunciationDemo()
      .then(setDemo)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'تعذّر تحميل مثال النطق.'));
  }, []);

  return (
    <article className="lab-card" aria-labelledby="pronunciation-title">
      <div className="lab-card__header">
        <span className="lab-card__icon"><SparkIcon /></span>
        <div>
          <span className="eyebrow">مختبر 01</span>
          <h3 id="pronunciation-title">تصحيح النطق</h3>
        </div>
      </div>
      <p className="lab-card__intro">قارن الكلمة نفسها قبل قاعدة النطق وبعدها، مع إبقاء الصوت والمزوّد ثابتين.</p>
      {error && <p className="notice notice--error" role="alert">{error}</p>}
      {demo ? (
        <>
          <div className="word-shift" aria-label="النص قبل التصحيح وبعده">
            <div><span>قبل</span><b>{demo.original_text}</b></div>
            <i aria-hidden="true">←</i>
            <div><span>بعد</span><b>{demo.corrected_text}</b></div>
          </div>
          <p className="provenance">لوحظ على {demo.provider_observed} · {demo.voice_observed}</p>
        </>
      ) : !error ? <div className="skeleton" aria-label="جارٍ تحميل مثال النطق" /> : null}
      <div className="audio-pair">
        <div className="audio-control"><span id="before-correction">قبل التصحيح</span><audio aria-labelledby="before-correction" controls preload="none" src="/api/pronunciation/demo/audio?corrected=false" /></div>
        <div className="audio-control"><span id="after-correction">بعد التصحيح</span><audio aria-labelledby="after-correction" controls preload="none" src="/api/pronunciation/demo/audio?corrected=true" /></div>
      </div>
    </article>
  );
}
