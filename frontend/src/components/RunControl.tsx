import type { Phase } from "../hooks/useCockpit";

export function RunControl({ phase, onStart }: { phase: Phase; onStart: () => void }) {
  const running = phase === "running";
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onStart}
        disabled={running}
        className="rounded bg-brand px-3 py-1.5 text-sm font-medium text-brand-ink hover:bg-brand-strong disabled:opacity-50"
      >
        Analyse starten
      </button>
      {running && <span className="text-sm text-muted">läuft …</span>}
    </div>
  );
}
