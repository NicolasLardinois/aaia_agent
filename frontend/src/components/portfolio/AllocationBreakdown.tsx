// Allokations-Aufschluesselung (Mangel #12): eine Dimension (Asset-Klasse/Sektor/Geographie)
// als beschriftete Anteils-Balken. Zeigt die VOLLE Verteilung — Ergaenzung zu den Klumpen-
// Warnungen, die nur Limit-Ueberschreitungen melden. Balkenlaenge = Anteil am Brutto-Exposure.
interface Slice { name: string; sharePct: number }

export function AllocationBreakdown({
  title, slices, labelFor,
}: { title: string; slices: Slice[]; labelFor?: (name: string) => string }) {
  return (
    <div>
      <h4 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{title}</h4>
      {slices.length === 0 ? (
        <p className="mt-2 text-sm text-muted">Keine Positionen.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {slices.map((s) => (
            <li key={s.name}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="truncate text-ink">{labelFor ? labelFor(s.name) : s.name}</span>
                <span className="tabular-nums text-muted">{s.sharePct} %</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
                {/* Breite = Anteil am Brutto (0..100 %); ehrliche absolute Laenge, direkt vergleichbar. */}
                <div className="h-full rounded-full bg-brand" style={{ width: `${Math.min(100, s.sharePct)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
