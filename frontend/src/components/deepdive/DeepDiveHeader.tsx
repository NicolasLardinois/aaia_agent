import type { DeepDiveView } from "../../contract/deepdive";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { UnavailableField } from "../UnavailableField";
import { VerdictGlance } from "./VerdictGlance";
import { Icon } from "../icons";
import { formatNumber } from "../../lib/format";

// Header (Konzept §4.5): beide Etiketten (underlying x wrapper) + Kurs/Markt + "vergleichen mit".
// Hero-Aufwertung (Mangel #13/#11): Ticker als grosse Schlagzeile, das Long/Short-Urteil rechts
// "auf einen Blick" (die These zuerst), ein Regime-Horizont-Akzent als Signatur. Bei "nicht
// gefunden" (found=false) entfaellt das Urteil — es gibt dann nichts zu deuten.
export function DeepDiveHeader({ view, onCompare }: { view: DeepDiveView; onCompare?: () => void }) {
  return (
    <header className="w-full space-y-3 border-b border-line pb-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-baseline gap-2">
            <h1 className="font-display text-2xl font-bold tracking-tight">{view.ticker}</h1>
            <span className="text-muted">·</span>
            <span className="text-lg text-muted">{view.name}</span>
          </div>
          <UnderlyingWrapperBadge underlying={view.underlying} wrapper={view.wrapper} />
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
            <span>
              Kurs:{" "}
              {view.price === null
                ? <UnavailableField reason="Kurs nicht verfügbar" />
                : <span className="tnum font-medium text-ink">{formatNumber(view.price)} {view.currency}</span>}
            </span>
            <span>· Markt: {view.market || "—"}</span>
            {onCompare && (
              <button
                type="button"
                onClick={onCompare}
                className="inline-flex items-center gap-1 text-brand underline-offset-2 hover:underline"
              >
                <Icon name="compare" className="h-3.5 w-3.5" />
                vergleichen mit
              </button>
            )}
          </div>
        </div>

        {view.found && (
          <VerdictGlance
            long={{ verdict: view.long.verdict, confidence: view.long.confidence }}
            short={{ verdict: view.short.verdict, confidence: view.short.confidence }}
          />
        )}
      </div>

      {/* Signatur-Akzent: Regime-Horizont (gleiche Bandfarbe wie im Cockpit) zieht eine ruhige
          Markenlinie unter den Kopf — verbindet Deep-Dive und Cockpit visuell. */}
      <div className="regime-horizon" aria-hidden="true" />
    </header>
  );
}
