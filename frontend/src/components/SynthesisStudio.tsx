import { useEffect, useMemo, useState } from 'react';
import { useObjectUrl } from '../hooks/useObjectUrl';
import { api } from '../lib/api';
import type {
  ArabicSample,
  Dialect,
  Emotion,
  ProcessedText,
  ProviderInfo,
  SynthesisResult,
  VoiceConfig,
} from '../types';
import { EyeIcon, PlayIcon, WaveIcon } from './Icons';
import { TextComparison } from './TextComparison';

const INITIAL_TEXT = 'مرحباً بكم، اليوم عندنا meeting الساعة 3 PM ومعنا 1,250.50 دولار وتاريخ 27/09/2026.';

const dialects: Array<[Dialect | '', string]> = [
  ['', 'تلقائي'],
  ['msa', 'فصحى'],
  ['gulf', 'خليجي'],
  ['egyptian', 'مصري'],
  ['levantine', 'شامي'],
  ['maghrebi', 'مغاربي'],
];

const emotions: Array<[Emotion, string]> = [
  ['neutral', 'محايد'],
  ['happy', 'سعيد'],
  ['excited', 'متحمس'],
  ['calm', 'هادئ'],
  ['warm', 'دافئ'],
  ['serious', 'جاد'],
];

interface SynthesisStudioProps {
  providers: ProviderInfo[];
  samples: ArabicSample[];
}

export function SynthesisStudio({ providers, samples }: SynthesisStudioProps) {
  const firstAvailable = providers.find((provider) => provider.status === 'available')?.id ?? '';
  const [text, setText] = useState(INITIAL_TEXT);
  const [provider, setProvider] = useState(firstAvailable);
  const [dialect, setDialect] = useState<Dialect | ''>('');
  const [gender, setGender] = useState('');
  const [voiceId, setVoiceId] = useState('');
  const [emotion, setEmotion] = useState<Emotion>('neutral');
  const [voices, setVoices] = useState<VoiceConfig[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [preview, setPreview] = useState<ProcessedText | null>(null);
  const [synthesis, setSynthesis] = useState<SynthesisResult | null>(null);
  const [busyAction, setBusyAction] = useState<'preview' | 'synthesize' | null>(null);
  const [error, setError] = useState('');
  const audioUrl = useObjectUrl(synthesis?.audio ?? null);

  useEffect(() => {
    if (!provider) {
      setVoices([]);
      return;
    }
    const controller = new AbortController();
    setVoicesLoading(true);
    api
      .voices(provider, controller.signal)
      .then(setVoices)
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setError(reason instanceof Error ? reason.message : 'تعذّر تحميل الأصوات.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setVoicesLoading(false);
      });
    return () => controller.abort();
  }, [provider]);

  const visibleVoices = useMemo(
    () => voices.filter((voice) => (!dialect || voice.dialect === dialect) && (!gender || voice.gender === gender)),
    [dialect, gender, voices],
  );

  useEffect(() => {
    if (voiceId && !visibleVoices.some((voice) => voice.id === voiceId)) setVoiceId('');
  }, [visibleVoices, voiceId]);

  const request = () => ({
    text,
    provider: provider || null,
    dialect: dialect || null,
    voice_id: voiceId || null,
    emotion,
    client_t0_ms: performance.now(),
  });

  const runPreview = async () => {
    setError('');
    setBusyAction('preview');
    try {
      setPreview(await api.preview(request()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'تعذّرت معاينة النص.');
    } finally {
      setBusyAction(null);
    }
  };

  const runSynthesis = async () => {
    setError('');
    setBusyAction('synthesize');
    try {
      setSynthesis(await api.synthesize(request()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'تعذّر توليد الصوت.');
    } finally {
      setBusyAction(null);
    }
  };

  const unavailable = providers.filter((item) => item.status !== 'available');
  return (
    <section className="studio" id="studio" aria-labelledby="studio-title">
      <div className="studio__composer">
        <div className="section-heading">
          <div>
            <span className="eyebrow">المسار الرئيسي</span>
            <h2 id="studio-title">اكتب النص، ثم استمع</h2>
          </div>
          <label className="sample-picker">
            <span>نص جاهز</span>
            <select
              name="sample"
              autoComplete="off"
              defaultValue=""
              onChange={(event) => {
                const sample = samples.find((item) => item.id === event.target.value);
                if (sample) setText(sample.text);
              }}
            >
              <option value="">اختر عيّنة</option>
              {samples.map((sample) => <option key={sample.id} value={sample.id}>{sample.description || sample.id}</option>)}
            </select>
          </label>
        </div>

        <label className="composer-field">
          <span className="sr-only">النص العربي</span>
          <textarea
            aria-label="النص العربي"
            name="text"
            autoComplete="off"
            value={text}
            maxLength={5000}
            onChange={(event) => setText(event.target.value)}
            placeholder="اكتب نصاً عربياً هنا…"
          />
          <span className="character-count" dir="ltr">{text.length} / 5000</span>
        </label>

        <div className="control-grid">
          <label className="field">
            <span>المزوّد</span>
            <select name="provider" autoComplete="off" value={provider} onChange={(event) => setProvider(event.target.value)}>
              {providers.map((item) => (
                <option key={item.id} value={item.id} disabled={item.status !== 'available'}>
                  {item.display_name}{item.status === 'available' ? '' : ' — غير متاح'}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>اللهجة</span>
            <select name="dialect" autoComplete="off" value={dialect} onChange={(event) => setDialect(event.target.value as Dialect | '')}>
              {dialects.map(([value, label]) => <option key={value || 'auto'} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="field">
            <span>الجنس</span>
            <select name="gender" autoComplete="off" value={gender} onChange={(event) => setGender(event.target.value)}>
              <option value="">أي صوت</option>
              <option value="female">أنثى</option>
              <option value="male">ذكر</option>
            </select>
          </label>
          <label className="field">
            <span>الصوت</span>
            <select name="voice" autoComplete="off" value={voiceId} onChange={(event) => setVoiceId(event.target.value)} disabled={voicesLoading}>
              <option value="">{voicesLoading ? 'جارٍ التحميل…' : 'اختيار تلقائي'}</option>
              {visibleVoices.map((voice) => <option key={voice.id} value={voice.id}>{voice.display_name} · {voice.locale}</option>)}
            </select>
          </label>
          <label className="field">
            <span>الأسلوب</span>
            <select name="emotion" autoComplete="off" value={emotion} onChange={(event) => setEmotion(event.target.value as Emotion)}>
              {emotions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        </div>

        {unavailable.length > 0 && (
          <details className="availability-note">
            <summary>{unavailable.length} مزوّد غير مفعّل</summary>
            <ul>
              {unavailable.map((item) => <li key={item.id}><b>{item.display_name}:</b> {item.unavailable_reason ?? item.status}</li>)}
            </ul>
          </details>
        )}

        {error && <p className="notice notice--error" role="alert">{error}</p>}

        <div className="action-row">
          <button className="button button--primary" onClick={runSynthesis} disabled={!text.trim() || !provider || busyAction !== null}>
            <PlayIcon />
            {busyAction === 'synthesize' ? 'جارٍ توليد الصوت…' : 'ولّد الصوت'}
          </button>
          <button className="button button--secondary" onClick={runPreview} disabled={!text.trim() || busyAction !== null}>
            <EyeIcon />
            {busyAction === 'preview' ? 'جارٍ التحليل…' : 'عاين المعالجة'}
          </button>
        </div>
      </div>

      <aside className="studio__result" aria-busy={busyAction === 'synthesize'} aria-live="polite">
        <div className="signal-rail" aria-hidden="true">
          {[12, 22, 34, 52, 30, 66, 42, 76, 48, 28, 56, 18].map((height, index) => (
            <i key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
        <span className="eyebrow eyebrow--light"><WaveIcon /> خرج الصوت</span>
        <h3>{synthesis ? 'الصوت جاهز' : 'بانتظار أول تجربة'}</h3>
        <p>{synthesis ? 'استمع إلى النتيجة وراجع بيانات التنفيذ.' : 'سيظهر التسجيل وملخّص التنفيذ هنا بعد التوليد.'}</p>
        {audioUrl && <audio className="audio-player audio-player--dark" controls autoPlay src={audioUrl} />}
        {synthesis && (
          <dl className="metric-list">
            <div><dt>المزوّد</dt><dd>{synthesis.provider ?? '—'}</dd></div>
            <div><dt>الصوت</dt><dd>{synthesis.voice ?? '—'}</dd></div>
            <div><dt>الزمن</dt><dd dir="ltr">{Math.round(synthesis.elapsedMs)} ms</dd></div>
            <div><dt>الأسلوب</dt><dd>{synthesis.emotionNative ? 'أصلي' : 'محاكاة نبرية'}</dd></div>
            <div><dt>المسار الاحتياطي</dt><dd>{synthesis.usedFallback ? 'استُخدم' : 'لم يُستخدم'}</dd></div>
          </dl>
        )}
      </aside>

      <div className="studio__comparison">
        <div className="section-heading section-heading--compact">
          <div>
            <span className="eyebrow">قابلية التتبّع</span>
            <h3>النص الأصلي والمعالَج</h3>
          </div>
        </div>
        <TextComparison result={preview} />
      </div>
    </section>
  );
}
