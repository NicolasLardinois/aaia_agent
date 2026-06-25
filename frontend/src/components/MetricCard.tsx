// Umrahmte Einzel-Kennzahl mit optional aufklappbarem Detail ("ausgewogenes" Design:
// Übersicht zuerst, Details auf Klick). null-Wert => "n.v.".
import { useState, type ReactNode } from "react";
import { InfoTip } from "./InfoTip";

export function MetricCard({
  label, value, unit, term, detail,
}: { label: string; value: string | number | null; unit?: string; term?: string; detail?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex items-center gap-1 text-xs text-slate-500">
        {label}
        {term && <InfoTip term={term} />}
      </div>
      <div className={`mt-1 text-lg ${missing ? "text-slate-400" : "font-semibold"}`}>{display}</div>
      {detail && (
        <>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            {open ? "Details ausblenden" : "Details"}
          </button>
          {open && <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">{detail}</div>}
        </>
      )}
    </div>
  );
}
