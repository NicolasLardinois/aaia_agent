import type { HedgeSuggestionDTO } from "../../contract/portfolio";

// Hedge-Vorschlaege (US26) — Track B ist BERATEND, KEINE Ausfuehrung (US27): bewusst keine
// Trade-Buttons, nur Anzeige. Jeder Vorschlag traegt seine Ableitung (rationale).
export function HedgeSuggestions({ hedges }: { hedges: HedgeSuggestionDTO[] }) {
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <h3 className="text-sm font-semibold">Hedge-Vorschläge</h3>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          beratend, keine Ausführung
        </span>
      </div>
      {hedges.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">Aktuell kein Hedge nötig (Kennzahlen im Rahmen).</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {hedges.map((h) => (
            <li key={h.id} className="rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
              <div>• {h.text}</div>
              <div className="text-xs text-slate-500">{h.rationale}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
