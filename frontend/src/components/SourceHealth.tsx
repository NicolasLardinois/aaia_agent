import { useState } from "react";
import { sourcesLabel } from "../lib/display";

export interface FailedSource { key: string; reason: string; }

// Verallgemeinerter Daten-Health-Zaehler (Konzept §5.4): x/y aktiv, Klick listet Ausfaelle.
export function SourceHealth({ active, total, failed = [] }: { active: number; total: number; failed?: FailedSource[] }) {
  const [open, setOpen] = useState(false);
  const allUp = active === total;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`text-sm ${allUp ? "text-slate-500" : "text-amber-600"}`}
      >
        <span>{sourcesLabel(active, total)}</span>{failed.length > 0 && <span> ⚠</span>}
      </button>
      {open && failed.length > 0 && (
        <ul className="absolute z-10 mt-1 rounded border border-slate-200 bg-white p-2 text-xs shadow dark:border-slate-700 dark:bg-slate-800">
          {failed.map((f) => (
            <li key={f.key}>{f.key}: {f.reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
