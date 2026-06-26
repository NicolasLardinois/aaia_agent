import { useState } from "react";
import { sourcesLabel } from "../lib/display";
import { Icon } from "./icons";

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
        className={`inline-flex items-center gap-1 text-sm ${allUp ? "text-muted" : "text-amber-600"}`}
      >
        <span>{sourcesLabel(active, total)}</span>
        {failed.length > 0 && <Icon name="warning" label="Quellen ausgefallen" className="h-3.5 w-3.5" />}
      </button>
      {open && failed.length > 0 && (
        <ul className="absolute z-10 mt-1 rounded border border-line bg-surface p-2 text-xs shadow">
          {failed.map((f) => (
            <li key={f.key}>{f.key}: {f.reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
