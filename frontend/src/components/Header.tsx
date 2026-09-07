import type { HealthResponse } from "../types/api";

const DEVICE_LABEL: Record<string, string> = {
  cuda: "CUDA",
  mps: "MPS",
  cpu: "CPU",
};

export function Header({ health }: { health: HealthResponse | null }) {
  return (
    <header className="site-header">
      <div className="site-header__identity">
        <span className="site-header__mark" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="30" height="30">
            <rect width="64" height="64" rx="14" fill="var(--teal)" />
            <path
              d="M14 34 L14 30 M22 40 L22 24 M30 46 L30 18 M38 40 L38 24 M46 34 L46 30"
              stroke="var(--surface)"
              strokeWidth="4.5"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </span>
        <div>
          <h1 className="site-header__title">لهجتنا</h1>
          <p className="site-header__subtitle">تحويل النص العربي إلى كلام، بلهجتك</p>
        </div>
      </div>

      <StatusPill health={health} />
    </header>
  );
}

function StatusPill({ health }: { health: HealthResponse | null }) {
  if (!health) {
    return (
      <span className="status-pill status-pill--loading">
        <span className="status-pill__dot" /> يتم الاتصال بالخادم…
      </span>
    );
  }
  if (health.status === "error") {
    return (
      <span className="status-pill status-pill--error">
        <span className="status-pill__dot" /> تعذّر تحميل النموذج
      </span>
    );
  }
  if (health.status === "loading") {
    return (
      <span className="status-pill status-pill--loading">
        <span className="status-pill__dot" /> جارٍ تحميل النموذج لأول مرة…
      </span>
    );
  }
  const deviceLabel = health.device ? DEVICE_LABEL[health.device] ?? health.device : null;
  return (
    <span className="status-pill status-pill--ok">
      <span className="status-pill__dot" />
      النموذج جاهز
      {deviceLabel && (
        <>
          {" "}
          · <span className="ltr-num">{deviceLabel}</span>
        </>
      )}
    </span>
  );
}
