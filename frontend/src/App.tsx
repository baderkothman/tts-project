import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, base64ToArrayBuffer, getDialects, getHealth, getModelInfo, synthesizeSpeech } from "./api/client";
import { AudioPlayer } from "./components/AudioPlayer";
import { useAvatarController } from "./components/avatar/useAvatarController";
import { AvatarStudioPanel } from "./components/avatar-studio/AvatarStudioPanel";
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

type AppTab = "tts" | "avatar";

export default function App() {
  const [activeTab, setActiveTab] = useState<AppTab>("tts");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [dialects, setDialects] = useState<Dialect[]>([]);

  const [text, setText] = useState("");
  const [mode, setMode] = useState<Mode>("voice_design");
  const [dialectId, setDialectId] = useState(DEFAULT_DIALECT_ID);
  const [gender, setGender] = useState<Gender | null>("female");
  const [pitch, setPitch] = useState<Pitch>("moderate pitch");
  const [refAudio, setRefAudio] = useState<File | null>(null);
  const [refText, setRefText] = useState("");
  const [speed, setSpeed] = useState(1);
  const [quality, setQuality] = useState<Quality>("high");
  // No longer user-adjustable (English-pronunciation handling was removed
  // from the settings UI) — the backend still needs a pipeline mode, so
  // "native" (let the Arabic model speak embedded English words itself) is
  // used unconditionally.
  const pipelineMode: PipelineMode = "native";

  const [aiDialectRewrite, setAiDialectRewrite] = useState(false);
  const [aiRewriteAvailable, setAiRewriteAvailable] = useState(false);

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

  // /api/model-info 503s until the TTS model finishes loading, so this
  // waits for health to report "ok" rather than firing once on mount.
  useEffect(() => {
    if (health?.status !== "ok") return;
    getModelInfo()
      .then((info) => setAiRewriteAvailable(info.dialect_rewriter_configured))
      .catch(() => setAiRewriteAvailable(false));
  }, [health?.status]);

  const selectedDialect = useMemo(() => dialects.find((d) => d.id === dialectId) ?? null, [dialects, dialectId]);

  const modelReady = health?.status === "ok";
  const { preview, loading: previewLoading, setPreview } = usePreprocessPreview(
    text,
    dialectId,
    pipelineMode,
    aiDialectRewrite,
    mode === "voice_design" ? gender : null,
  );
  const { state: streamState, start: startStream, stop: stopStream } = useStreamingSynthesis();

  const avatarState = useAvatarController({
    connected: health !== null,
    hasError: health?.status === "error" || error !== null,
    modelLoading: health?.status === "loading",
    generating: loading,
    streamingActive: streamState.active,
    // audioUrl is a fresh blob: URL per successful generation (or null before
    // the first one / after reset), so it doubles as a "new result" token.
    resultToken: audioUrl,
  });

  const buildTtsParams = useCallback(
    (): TTSRequestParams => ({
      text,
      mode,
      pipeline_mode: pipelineMode,
      dialect_id: dialectId,
      gender: mode === "voice_design" ? gender : null,
      pitch,
      ref_text: mode === "clone" ? refText || null : null,
      speed,
      quality,
      guidance_scale: 2.0,
      ref_audio: mode === "clone" ? refAudio : null,
      ai_dialect_rewrite: aiDialectRewrite,
    }),
    [text, mode, pipelineMode, dialectId, gender, pitch, refText, speed, quality, refAudio, aiDialectRewrite],
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
      const params = buildTtsParams();
      const response = await synthesizeSpeech(params);

      const buffer = base64ToArrayBuffer(response.audio_base64);
      const blob = new Blob([buffer], { type: response.content_type });
      const url = URL.createObjectURL(blob);

      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = url;

      setResult(response);
      setAudioUrl(url);
      setAudioBuffer(buffer);
      // Make the "ready to be spoken" panel authoritative for the audio
      // that just loaded: /api/tts ran its own, independent preprocessing
      // pass (a fresh OpenAI call when AI dialect rewrite is on), which can
      // legitimately return different wording than the live preview's last
      // pass — this is what was actually spoken, so it must be what's shown.
      // `params.text` (not the possibly-since-edited `text` state) is what
      // this specific response corresponds to.
      setPreview({
        original_text: params.text,
        processed_text: response.processed_text,
        segments: response.segments,
        warnings: response.warnings,
      });
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
        <Header health={health} avatarState={avatarState} />

        <nav className="mode-tabs" role="tablist" aria-label="وضع الاستخدام">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "tts"}
            className={`mode-tabs__option${activeTab === "tts" ? " mode-tabs__option--active" : ""}`}
            onClick={() => setActiveTab("tts")}
          >
            توليد الصوت
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "avatar"}
            className={`mode-tabs__option${activeTab === "avatar" ? " mode-tabs__option--active" : ""}`}
            onClick={() => setActiveTab("avatar")}
          >
            الصورة الناطقة
          </button>
        </nav>

        {activeTab === "avatar" ? (
          <AvatarStudioPanel
            dialects={dialects.length ? dialects : FALLBACK_DIALECTS}
            modelReady={modelReady}
            aiRewriteAvailable={aiRewriteAvailable}
          />
        ) : (
        <main className="composer-card">
          {/* DOM order = visual order in this RTL layout: مساحة العمل (right) -> إعدادات (left).
              Text, its live preview, the generate action, and the result all
              live in one column — they're one continuous task (write, see
              what will be spoken, act, listen), not three unrelated panels;
              a separate "audio" column here used to sit mostly empty until
              generation finished, and still had a lot of dead space below
              the player even after. */}
          <section className="composer-col composer-col--workspace">
            <TextComposer value={text} onChange={setText} />
            <PreprocessPreview preview={preview} loading={previewLoading} />

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
              aiRewrite={aiDialectRewrite}
              onAiRewriteChange={setAiDialectRewrite}
              aiRewriteAvailable={aiRewriteAvailable}
            />

            <VoicePanel
              mode={mode}
              onModeChange={setMode}
              gender={gender}
              onGenderChange={setGender}
              pitch={pitch}
              onPitchChange={setPitch}
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
        )}

        <footer className="page__footer">
          <p>
            التوليد الصوتي مدعوم حصرًا بنموذج{" "}
            <span className="ltr-num" dir="ltr">
              oddadmix/lahgtna-omnivoice-v2
            </span>{" "}
            ويعمل محليًا بالكامل. إعادة الصياغة اللهجية الاختيارية عبر OpenAI هي الاستثناء الوحيد
            الذي يُرسل النص إلى مزوّد خارجي.
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
