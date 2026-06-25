// Kompakte Kennzahl-Zeile: Label (+ optionalem Erklär-Tooltip) links, Wert rechts.
// null-Wert => "n.v." (UNAVAILABLE ≠ 0).
import { InfoTip } from "./InfoTip";

export function MetricRow({
  label, value, unit, term,
}: { label: string; value: string | number | null; unit?: string; term?: string }) {
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-1.5 text-sm last:border-0 dark:border-slate-700/50">
      <span className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
        {label}
        {term && <InfoTip term={term} />}
      </span>
      <span className={missing ? "text-slate-400" : "font-medium"}>{display}</span>
    </div>
  );
}
