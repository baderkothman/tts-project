export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      <button type="button" className="error-banner__dismiss" onClick={onDismiss} aria-label="إغلاق التنبيه">
        ×
      </button>
    </div>
  );
}
