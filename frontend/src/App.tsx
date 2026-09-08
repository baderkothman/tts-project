import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, base64ToArrayBuffer, getDialects, getHealth, synthesizeSpeech } from "./api/client";
import { AudioPlayer } from "./components/AudioPlayer";
import { DialectRail } from "./components/DialectRail";
import { ErrorBanner } from "./components/ErrorBanner";
import { GenerationControls } from "./components/GenerationControls";
import { Header } from "./components/Header";
import { PreprocessPreview } from "./components/PreprocessPreview";
import { StreamingDemo } from "./components/StreamingDemo";
import { TextComposer } from "./components/TextComposer";
import { VoicePanel } from "./components/VoicePanel";
import { usePreprocessPreview } from "./hooks/usePreprocessPreview";
import { useStreamingSynthesis } from "./hooks/useStreamingSynthesis";
import "./app.css";
import type {
  AgeGroup,
  Dialect,
  Gender,
  HealthResponse,
  Mode,
  PipelineMode,
  Pitch,
  Quality,
  TTSRequestParams,
  TTSResponse,
} from "./types/api";

const DEFAULT_DIALECT_ID = "msa";

// The backend keeps error strings terse and English (they're an API
// contract, not UI copy). Translate the predictable ones here; anything
// unrecognized still reaches the user in full rather than being swallowed.
const KNOWN_ERROR_TRANSLATIONS: [RegExp, string][] = [
  [/not loaded/i, "النموذج ما زال قيد التحميل — انتظر لحظات وحاول مجددًا."],
  [/reference audio.*could not be decoded|could not be decoded/i, "تعذّر قراءة الملف الصوتي — تأكد أنه WAV أو MP3 أو FLAC أو OGG صالح."],
  [/unsupported reference audio type/i, "صيغة الملف الصوتي غير مدعومة."],
  [/exceeds the .*limit/i, "حجم الملف الصوتي يتجاوز الحد المسموح به."],
  [/requires a reference audio file/i, "استنساخ الصوت يتطلب رفع عيّنة صوتية أولًا."],
  [/speech generation failed/i, "تعذّر توليد الصوت. حاول مجددًا بنص مختلف أو أقصر."],
];

function translateError(message: string): string {
  for (const [pattern, arabic] of KNOWN_ERROR_TRANSLATIONS) {
    if (pattern.test(message)) return arabic;
  }
  return message;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [dialects, setDialects] = useState<Dialect[]>([]);

  const [text, setText] = useState("");
  const [mode, setMode] = useState<Mode>("voice_design");
  const [dialectId, setDialectId] = useState(DEFAULT_DIALECT_ID);
  const [gender, setGender] = useState<Gender | null>("female");
  const [pitch, setPitch] = useState<Pitch>("moderate pitch");
  const [age, setAge] = useState<AgeGroup | null>(null);
  const [whisper, setWhisper] = useState(false);
  const [refAudio, setRefAudio] = useState<File | null>(null);
  const [refText, setRefText] = useState("");
  const [speed, setSpeed] = useState(1);
  const [quality, setQuality] = useState<Quality>("high");
  // No longer user-adjustable (English-pronunciation handling was removed
  // from the settings UI) — the backend still needs a pipeline mode, so
  // "native" (let the Arabic model speak embedded English words itself) is
  // used unconditionally.
  const pipelineMode: PipelineMode = "native";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TTSResponse | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioBuffer, setAudioBuffer] = useState<ArrayBuffer | null>(null);

  const audioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: number;

    async function poll() {
      try {
        const h = await getHealth();
        if (!cancelled) setHealth(h);
        if (!cancelled && h.status !== "ok") {
          timer = window.setTimeout(poll, 2500);
        }
      } catch {
        if (!cancelled) setHealth({ status: "error", model_loaded: false, detail: "الخادم غير متاح" });
      }
    }
    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    getDialects()
      .then(setDialects)
      .catch(() => setDialects([]));
  }, []);

  const selectedDialect = useMemo(() => dialects.find((d) => d.id === dialectId) ?? null, [dialects, dialectId]);

  const modelReady = health?.status === "ok";
  const { preview, loading: previewLoading } = usePreprocessPreview(text, dialectId, pipelineMode);
  const { state: streamState, start: startStream, stop: stopStream } = useStreamingSynthesis();

  const buildTtsParams = useCallback(
    (): TTSRequestParams => ({
      text,
      mode,
      pipeline_mode: pipelineMode,
      dialect_id: dialectId,
      gender: mode === "voice_design" ? gender : null,
      pitch,
      age: mode === "voice_design" ? age : null,
      whisper: mode === "voice_design" ? whisper : false,
      ref_text: mode === "clone" ? refText || null : null,
      speed,
      quality,
      guidance_scale: 2.0,
      ref_audio: mode === "clone" ? refAudio : null,
    }),
    [text, mode, pipelineMode, dialectId, gender, pitch, age, whisper, refText, speed, quality, refAudio],
  );

  const handleGenerate = useCallback(async () => {
    if (!text.trim()) {
      setError("اكتب نصًا أولًا");
      return;
    }
    if (mode === "clone" && !refAudio) {
      setError("استنساخ الصوت يتطلب رفع عيّنة صوتية أولًا");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await synthesizeSpeech(buildTtsParams());

      const buffer = base64ToArrayBuffer(response.audio_base64);
      const blob = new Blob([buffer], { type: response.content_type });
      const url = URL.createObjectURL(blob);

      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = url;

      setResult(response);
      setAudioUrl(url);
      setAudioBuffer(buffer);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(translateError(err.message));
      } else {
        setError("تعذّر الاتصال بالخادم. تحقّق من تشغيل الخادم الخلفي وحاول مجددًا.");
      }
    } finally {
      setLoading(false);
    }
  }, [text, mode, refAudio, buildTtsParams]);

  const handleStreamToggle = useCallback(() => {
    if (streamState.active) {
      stopStream();
      return;
    }
    if (!text.trim()) {
      setError("اكتب نصًا أولًا");
      return;
    }
    if (mode === "clone" && !refAudio) {
      setError("استنساخ الصوت يتطلب رفع عيّنة صوتية أولًا");
      return;
    }
    setError(null);
    void startStream(buildTtsParams());
  }, [streamState.active, stopStream, text, mode, refAudio, buildTtsParams, startStream]);

  function handleReset() {
    setText("");
    setResult(null);
    setError(null);
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setAudioUrl(null);
    setAudioBuffer(null);
  }

  return (
    <div className="page">
      <div className="page__container">
        <Header health={health} />

        <main className="composer-card">
          {/* DOM order = visual order in this RTL layout: نص (right) -> صوت (middle) -> إعدادات (left) */}
          <section className="composer-col composer-col--text">
            <TextComposer value={text} onChange={setText} />
            <PreprocessPreview preview={preview} loading={previewLoading} />
          </section>

          <section className="composer-col composer-col--audio">
            {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

            <div className="actions">
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleGenerate}
                disabled={loading || !modelReady || !text.trim()}
              >
                {loading ? (
                  <>
                    <LoadingBars /> جارٍ التوليد…
                  </>
                ) : (
                  "ولّد الصوت"
                )}
              </button>
              <button type="button" className="btn btn--ghost" onClick={handleReset} disabled={loading}>
                مسح
              </button>
            </div>

            <StreamingDemo state={streamState} onToggle={handleStreamToggle} disabled={loading || !modelReady} />

            {result && audioUrl && audioBuffer && (
              <AudioPlayer
                result={result}
                audioUrl={audioUrl}
                arrayBuffer={audioBuffer}
                dialect={selectedDialect}
                fileNameHint={`lahgtna-${dialectId}`}
              />
            )}
          </section>

          <section className="composer-col composer-col--settings">
            <DialectRail
              dialects={dialects.length ? dialects : FALLBACK_DIALECTS}
              selectedId={dialectId}
              onSelect={setDialectId}
            />

            <VoicePanel
              mode={mode}
              onModeChange={setMode}
              gender={gender}
              onGenderChange={setGender}
              pitch={pitch}
              onPitchChange={setPitch}
              age={age}
              onAgeChange={setAge}
              whisper={whisper}
              onWhisperChange={setWhisper}
              refAudio={refAudio}
              onRefAudioChange={setRefAudio}
              refText={refText}
              onRefTextChange={setRefText}
            />

            <GenerationControls
              speed={speed}
              onSpeedChange={setSpeed}
              quality={quality}
              onQualityChange={setQuality}
            />
          </section>
        </main>

        <footer className="page__footer">
          <p>
            مدعوم حصرًا بنموذج{" "}
            <span className="ltr-num" dir="ltr">
              oddadmix/lahgtna-omnivoice-v2
            </span>{" "}
            — يعمل محليًا بالكامل، بلا أي مزوّد خارجي.
          </p>
        </footer>
      </div>
    </div>
  );
}

function LoadingBars() {
  return (
    <span className="loading-bars" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </span>
  );
}

// Shown only for the instant before /api/dialects resolves.
const FALLBACK_DIALECTS: Dialect[] = [
  { id: "msa", name_en: "Modern Standard Arabic", name_ar: "الفصحى", language_code: "arb", written_only: false },
];
