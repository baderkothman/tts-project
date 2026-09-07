import { useState } from 'react';
import { useObjectUrl } from '../hooks/useObjectUrl';
import { api, audioFromBase64 } from '../lib/api';
import type { DialectComparison } from '../types';
import { CompareIcon } from './Icons';

const DEFAULT_TEXT = 'بكرا عندي meeting عالـ 10، وبعدها بدنا نعمل deploy للـ API.';

export function DialectLab() {
  const [text, setText] = useState(DEFAULT_TEXT);
  const [dialect, setDialect] = useState('');
  const [result, setResult] = useState<DialectComparison | null>(null);
  const [rawAudio, setRawAudio] = useState<Blob | null>(null);
  const [correctedAudio, setCorrectedAudio] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const rawUrl = useObjectUrl(rawAudio);
  const correctedUrl = useObjectUrl(correctedAudio);

  const compare = async () => {
    setLoading(true);
    setError('');
    try {
      const comparison = await api.compareDialect(text, dialect || null);
      setResult(comparison);
      setRawAudio(audioFromBase64(comparison.raw_audio_ref));
      setCorrectedAudio(audioFromBase64(comparison.corrected_audio_ref));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'تعذّرت مقارنة اللهجة.');
    } finally {
      setLoading(false);
    }
  };

  const detectionSource = result?.detection.source === 'user_selected' ? 'اختيارك' : 'الكشف التلقائي';
  const confidence = result?.detection.classifier_confidence;

  return (
    <article className="lab-card lab-card--wide" aria-labelledby="dialect-title">
      <div className="lab-card__header">
        <span className="lab-card__icon"><CompareIcon /></span>
        <div>
          <span className="eyebrow">مختبر 02</span>
          <h3 id="dialect-title">مقارنة اللهجة</h3>
        </div>
      </div>
      <p className="lab-card__intro">استمع إلى النص الخام والمصحّح، واعرف كيف حُدّدت اللهجة وما الذي تغيّر.</p>
      <label className="composer-field composer-field--small">
        <span className="sr-only">نص مقارنة اللهجة</span>
        <textarea aria-label="نص مقارنة اللهجة" name="dialect-comparison-text" autoComplete="off" value={text} maxLength={5000} onChange={(event) => setText(event.target.value)} />
      </label>
      <div className="inline-controls">
        <label className="field">
          <span>اللهجة</span>
          <select name="comparison-dialect" autoComplete="off" value={dialect} onChange={(event) => setDialect(event.target.value)}>
            <option value="">كشف تلقائي</option>
            <option value="msa">فصحى</option>
            <option value="levantine">شامي عام</option>
            <option value="lebanese">لبناني</option>
            <option value="gulf">خليجي عام</option>
            <option value="saudi">سعودي</option>
            <option value="egyptian">مصري</option>
          </select>
        </label>
        <button className="button button--ink" onClick={compare} disabled={!text.trim() || loading}>
          <CompareIcon /> {loading ? 'جارٍ المقارنة…' : 'قارن النتيجتين'}
        </button>
      </div>
      {error && <p className="notice notice--error" role="alert">{error}</p>}
      {result && (
        <div className="dialect-result" aria-live="polite">
          <div className="result-summary">
            <span><small>اللهجة المعتمدة</small><b>{result.detection.resolved_dialect}</b></span>
            <span><small>مصدر القرار</small><b>{detectionSource}</b></span>
            {confidence != null && <span><small>ثقة المصنّف</small><b dir="ltr">{Math.round(confidence * 100)}%</b></span>}
          </div>
          {result.detection.unavailable_reason && <p className="notice">{result.detection.unavailable_reason}</p>}
          <div className="change-list">
            <span className="eyebrow">ما الذي تغيّر؟</span>
            <p>{result.changes.length ? result.changes.join('، ') : 'لا يوجد تصحيح قابل للتطبيق.'}</p>
            <p className="architecture-note">المسار: {result.architecture_used}</p>
          </div>
          <div className="audio-pair">
            <div className="audio-control"><span id="raw-dialect-audio">النطق الخام</span><audio aria-labelledby="raw-dialect-audio" controls src={rawUrl} /></div>
            <div className="audio-control"><span id="corrected-dialect-audio">النطق المصحّح</span><audio aria-labelledby="corrected-dialect-audio" controls src={correctedUrl} /></div>
          </div>
        </div>
      )}
    </article>
  );
}
