// Umrahmte Einzel-Kennzahl mit optional aufklappbarem Detail ("ausgewogenes" Design:
// Übersicht zuerst, Details auf Klick). Wert als Mono-Ablesung. null-Wert => "n.v.".
import { useState, type ReactNode } from "react";
import { InfoTip } from "./InfoTip";

export function MetricCard({
  label, value, unit, term, detail,
}: { label: string; value: string | number | null; unit?: string; term?: string; detail?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3">
      <div className="flex items-center gap-1 text-xs text-muted">
        <span>{label}</span>
        {term && <InfoTip term={term} />}
      </div>
      <div className={`mt-1 font-mono tnum text-lg ${missing ? "text-muted/70" : "font-semibold text-ink"}`}>{display}</div>
      {detail && (
        <>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="mt-1 text-xs text-brand hover:underline"
          >
            {open ? "Details ausblenden" : "Details"}
          </button>
          {open && <div className="mt-2 text-sm text-muted">{detail}</div>}
        </>
      )}
    </div>
  );
}
