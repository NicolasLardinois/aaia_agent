import type { DeepDiveView } from "../../contract/deepdive";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { rollYieldVisual, leverageFactor } from "../../lib/futures";
import { verdictToVisual } from "../../lib/judgment";

// Roll-Yield-Zelle: Future -> Vorzeichen + %/Jahr; sonst "kein Roll" (physisch/Fund).
function rollCell(v: DeepDiveView) {
  if (!v.futures) return <span className="text-slate-500">— (kein Roll)</span>;
  const r = rollYieldVisual(v.futures.rollYieldAnnualPct, v.futures.form);
  return (
    <span className={r.colorClass}>
      {v.futures.rollYieldAnnualPct >= 0 ? "+" : ""}{v.futures.rollYieldAnnualPct} %/Jahr {r.arrow}
    </span>
  );
}

// Hebel-Zelle: Future -> effektiver Hebel (Nominal/Margin); sonst 1x (voll besichert).
function levCell(v: DeepDiveView) {
  if (!v.futures) return <span>1× (voll besichert)</span>;
  return <span>≈ {leverageFactor(v.futures.notional, v.futures.marginInitial).toFixed(1)}×</span>;
}

// Urteil-Zelle: Long-Verdict + Konfidenz %.
function verdictCell(v: DeepDiveView) {
  const vis = verdictToVisual(v.long.verdict);
  return (
    <span className={vis.colorClass}>
      {vis.label} {Math.round(v.long.confidence * 100)} %
    </span>
  );
}

// Vergleichsmodus (US11, Konzept §5.2): gleicher underlying, zwei wrapper nebeneinander.
// Zeigt Roll-Yield (Future negativ = Gegenwind, ohne Future = kein Roll), effektiver Hebel
// (1x bei physisch/Fund), laufende Kosten, Gegenparteirisiko und Long-Urteil je Wrapper —
// damit der Nutzer die Hüllenwahl informiert treffen kann (z. B. GC=F Future HOLD vs. 4GLD physisch BUY).
export function CompareView({ left, right }: { left: DeepDiveView; right: DeepDiveView }) {
  const cols = [left, right];
  const Row = ({
    label,
    render,
  }: {
    label: string;
    render: (v: DeepDiveView) => React.ReactNode;
  }) => (
    <tr>
      <th className="py-1 pr-4 text-left font-medium text-slate-500">{label}</th>
      {cols.map((c) => (
        <td key={c.ticker} className="py-1 pr-4">
          {render(c)}
        </td>
      ))}
    </tr>
  );

  return (
    <table className="text-sm">
      <thead>
        <tr>
          <th />
          {cols.map((c) => (
            <th key={c.ticker} className="py-1 pr-4 text-left font-semibold">
              {c.ticker}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <Row label="Basiswert" render={(v) => v.name} />
        <Row
          label="Hülle"
          render={(v) => (
            <UnderlyingWrapperBadge underlying={v.underlying} wrapper={v.wrapper} />
          )}
        />
        <Row label="Roll-Yield" render={rollCell} />
        <Row label="Hebel" render={levCell} />
        <Row label="Laufende Kosten" render={(v) => v.runningCosts ?? "—"} />
        <Row label="Gegenparteirisiko" render={(v) => v.counterpartyRisk ?? "—"} />
        <Row label="Long-Urteil" render={verdictCell} />
      </tbody>
    </table>
  );
}
