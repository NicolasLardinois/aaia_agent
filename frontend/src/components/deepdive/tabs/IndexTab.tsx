import type { IndexBlockDTO } from "../../../contract/deepdive";
import { formatNumber } from "../../../lib/format";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

// index-Variante (US15): Bewertung, Breadth (Marktbreite), Momentum, Sektorkomposition —
// zeigt, ob ein Index breit getragen oder von wenigen Titeln getrieben ist.
export function IndexTab({ block }: { block: IndexBlockDTO }) {
  return (
    <div className="space-y-2 text-sm">
      <div>
        Index-KGV:{" "}
        {block.valuationPe === null ? (
          <UnavailableField />
        ) : (
          <span className="font-medium">{formatNumber(block.valuationPe)}</span>
        )}
      </div>
      <div>
        Breadth:{" "}
        {block.breadthPct === null ? (
          <UnavailableField />
        ) : (
          <span className="font-medium">{formatNumber(block.breadthPct)} % über 200-Tage-Linie</span>
        )}
      </div>
      <div>Momentum: <SignalBadge signal={block.momentumSignal} /></div>
      <div>
        <div className="text-xs uppercase text-slate-500">Sektorkomposition</div>
        <ul>
          {block.composition.map((c) => (
            <li key={c.sector}>{c.sector}: {formatNumber(c.weightPct)} %</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
