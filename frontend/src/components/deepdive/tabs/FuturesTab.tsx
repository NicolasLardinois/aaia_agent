import type { FuturesBlockDTO } from "../../../contract/deepdive";
import { LineCurve } from "../../charts/LineCurve";
import { rollYieldVisual, leverageFactor } from "../../../lib/futures";
import { formatNumber, formatSigned } from "../../../lib/format";

// Futures-Tab (US33–36, Konzept §5.1): Terminkurve (Contango = aufwärts, Backwardation = abwärts)
// über LineCurve; Roll-Yield mit Vorzeichen und Richtung benannt (Contango < 0 = Gegenwind,
// Backwardation > 0 = Rückenwind — AGENTS.md §3); Verfall + nächster Roll-Termin; Hebel = Nominal/Margin.
export function FuturesTab({ block }: { block: FuturesBlockDTO }) {
  const roll = rollYieldVisual(block.rollYieldAnnualPct, block.form);
  const lev = leverageFactor(block.notional, block.marginInitial);
  return (
    <div className="space-y-4 text-sm">
      <LineCurve
        series={[{
          name: "Terminkurve",
          points: block.curve.map((p) => ({ x: p.contractMonth, y: p.price })),
        }]}
        height={200}
      />
      <div>Form: <span className="font-medium uppercase">{block.form}</span></div>
      <div>
        Roll-Yield:{" "}
        <span className={`font-medium ${roll.colorClass}`}>
          {formatSigned(block.rollYieldAnnualPct)} %/Jahr {roll.arrow}
        </span>{" "}
        <span className="text-slate-500">({roll.label})</span>
      </div>
      <div>Verfall aktueller Kontrakt: <span className="font-medium">{block.expiryDate}</span></div>
      <div>Nächster Roll-Termin: <span className="font-medium">{block.nextRollDate}</span></div>
      <div>
        {/* Nominalwert + Margin zeigen, damit der Hebel nachvollziehbar ist (Herleitung: Nominal / Margin) */}
        Nominal: <span className="font-medium">{formatNumber(block.notional)}</span>{" "}
        · Margin (Initial): <span className="font-medium">{formatNumber(block.marginInitial)}</span>{" "}
        → Hebel ≈ {formatNumber(lev, 1)}×
      </div>
    </div>
  );
}
