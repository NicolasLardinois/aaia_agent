import type { LongShortSplit } from "../../lib/composition";

// Long/Short-Balance (Mangel #12): ein geteilter Balken (Brutto-Long gruen | Brutto-Short rot)
// plus Netto-Marktrichtung. Macht die Long-Short-/Total-Return-Idee sichtbar — wie viel Kapital
// auf steigende vs. fallende Kurse wettet. Der Balken IST das Brutto, nach Richtung aufgeteilt.
export function LongShortBalance({ split }: { split: LongShortSplit }) {
  const total = split.grossLongPct + split.grossShortPct;
  const longW = total ? (split.grossLongPct / total) * 100 : 0;
  const shortW = total ? (split.grossShortPct / total) * 100 : 0;
  const net = `${split.netPct >= 0 ? "+" : ""}${split.netPct}`;
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium text-bull">Long {split.grossLongPct} % · {split.longCount}</span>
        <span className="font-medium text-bear">Short {split.grossShortPct} % · {split.shortCount}</span>
      </div>
      <div
        className="mt-1 flex h-2.5 overflow-hidden rounded-full bg-surface-2"
        role="img"
        aria-label={`Long ${split.grossLongPct} Prozent, Short ${split.grossShortPct} Prozent, Netto ${net} Prozent`}
      >
        <div className="h-full bg-bull" style={{ width: `${longW}%` }} />
        <div className="h-full bg-bear" style={{ width: `${shortW}%` }} />
      </div>
      <div className="mt-1.5 text-xs text-muted">
        Netto-Marktrichtung: <span className="font-medium text-ink">{net} %</span>
      </div>
    </div>
  );
}
