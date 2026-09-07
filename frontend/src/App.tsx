import { useEffect, useState } from 'react';
import { DialectLab } from './components/DialectLab';
import { PronunciationLab } from './components/PronunciationLab';
import { SynthesisStudio } from './components/SynthesisStudio';
import { WaveIcon } from './components/Icons';
import { api } from './lib/api';
import type { ArabicSample, ProviderInfo } from './types';

export default function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [samples, setSamples] = useState<ArabicSample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.providers(), api.samples()])
      .then(([nextProviders, nextSamples]) => {
        setProviders(nextProviders);
        setSamples(nextSamples);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'تعذّر الاتصال بالخدمة.'))
      .finally(() => setLoading(false));
  }, []);

  const availableCount = providers.filter((provider) => provider.status === 'available').length;
  return (
    <>
      <a className="skip-link" href="#main-content">انتقل إلى المحتوى الرئيسي</a>
      <header className="site-header" id="top">
        <a className="brand" href="#top" aria-label="مرسم الصوت العربي — الصفحة الرئيسية">
          <span className="brand__mark"><WaveIcon /></span>
          <span><b>مرسم الصوت</b><small>العربي</small></span>
        </a>
        <nav aria-label="التنقل الرئيسي">
          <a href="#studio">التوليد</a>
          <a href="#labs">مختبرات النطق</a>
        </nav>
        <span className="service-status" title="عدد مزوّدي الصوت المتاحين" aria-live="polite">
          <i aria-hidden="true" /> {loading ? 'جارٍ الاتصال' : `${availableCount} متاح`}
        </span>
      </header>

      <main id="main-content">
        <section className="hero">
          <div className="hero__copy">
            <span className="eyebrow">تجربة صوتية عربية قابلة للقياس</span>
            <h1>من النص إلى<br /><em>صوتٍ واضح.</em></h1>
            <p>اكتب بالعربية، اختر اللهجة والصوت، ثم راقب كيف عالج النظام النص قبل أن تسمعه.</p>
          </div>
          <div className="hero__annotation" aria-label="مراحل التجربة">
            <span>نص</span><i /><span>معالجة</span><i /><span>صوت</span>
          </div>
        </section>

        {error ? (
          <section className="fatal-state" role="alert">
            <h2>تعذّر فتح مساحة العمل</h2>
            <p>{error}</p>
            <button className="button button--primary" onClick={() => window.location.reload()}>أعد المحاولة</button>
          </section>
        ) : loading ? (
          <section className="loading-state" aria-label="جارٍ تجهيز مساحة العمل">
            <span /><span /><span />
          </section>
        ) : (
          <SynthesisStudio providers={providers} samples={samples} />
        )}

        <section className="labs" id="labs" aria-labelledby="labs-title">
          <div className="section-heading section-heading--page">
            <div>
              <span className="eyebrow">استمع إلى الفروق</span>
              <h2 id="labs-title">مختبرات النطق واللهجة</h2>
            </div>
            <p>أدوات مقارنة صغيرة تشرح النتيجة بدلاً من إخفائها.</p>
          </div>
          <div className="labs__grid">
            <PronunciationLab />
            <DialectLab />
          </div>
        </section>
      </main>

      <footer>
        <span translate="no">Arabic TTS Prototype</span>
        <span>القرار اللغوي في الخادم، والتجربة هنا.</span>
      </footer>
    </>
  );
}
