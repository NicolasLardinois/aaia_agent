import { regimeInsight } from "../lib/regimeInsight";
import { Icon } from "./icons";

// ---- Regime-Deutung: erklaert die aktuelle Konjunkturphase fuer Laien ----
// Bildungs-Panel der Cockpit-Uebersicht (#4): uebersetzt das Marktregime in
// Klartext + typische Anlageklassen-Tendenzen (Investment-Clock, siehe
// lib/regimeInsight). Bewusst als "typische Tendenz, kein Automatismus" gerahmt.
export function RegimeInsightCard({ regime }: { regime: string }) {
  const i = regimeInsight(regime);

  return (
    <section className="rounded-lg border border-line p-4">
      <div className="flex items-center gap-2">
        <Icon name="compass" className="h-4 w-4 text-muted" />
        <h2 className="text-xs uppercase tracking-wide text-muted">Was das Regime bedeutet</h2>
      </div>

      <p className="mt-1 text-base font-semibold text-ink">Was bedeutet {i.phase}?</p>
      <p className="mt-1 text-sm text-muted">{i.summary}</p>

      {i.known && (
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex items-start gap-2">
            <Icon name="trend-up" className="mt-0.5 h-4 w-4 shrink-0 text-bull" />
            <div>
              <dt className="font-medium text-ink">Im Vorteil</dt>
              <dd className="text-muted">{i.favored}</dd>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div>
              <dt className="font-medium text-ink">Vorsicht</dt>
              <dd className="text-muted">{i.caution}</dd>
            </div>
          </div>
        </dl>
      )}

      <p className="mt-3 text-xs text-muted">
        Typische Tendenzen aus dem Konjunkturzyklus — kein Automatismus und kein Timing-Signal.
      </p>
    </section>
  );
}
