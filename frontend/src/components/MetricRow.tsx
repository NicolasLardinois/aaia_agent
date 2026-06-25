// Kompakte Kennzahl-Zeile: Label (+ optionalem Erklär-Tooltip) links, Wert rechts.
// Wert als Mono-Ablesung (tabellarische Ziffern) — die "Instrument-Deck"-Signatur.
// null-Wert => "n.v." (UNAVAILABLE ≠ 0).
import { InfoTip } from "./InfoTip";

export function MetricRow({
  label, value, unit, term,
}: { label: string; value: string | number | null; unit?: string; term?: string }) {
  const missing = value === null || value === undefined;
  const display = missing ? "n.v." : `${value}${unit ? ` ${unit}` : ""}`;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-1.5 text-sm last:border-0">
      <span className="flex items-center gap-1 text-muted">
        <span>{label}</span>
        {term && <InfoTip term={term} />}
      </span>
      <span className={`font-mono tnum ${missing ? "text-muted/70" : "font-medium text-ink"}`}>{display}</span>
    </div>
  );
}
