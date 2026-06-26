import { useView } from "../../data/useView";
import { loadYieldCurve } from "../../data/cockpit";
import { yieldSpreadStatus } from "../../lib/curve";
import { LineCurve } from "../../components/charts/LineCurve";
import { Icon } from "../../components/icons";
import { DrilldownShell } from "./DrilldownShell";
import type { YieldCurveView, SpreadRow } from "../../contract/cockpit";

// Vorzeichen-Formatierung für Spread-Wert (explizit +/− nennen, AGENTS.md §3).
function formatSpread(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)} %-Pkt.`;
}

function SpreadItem({ row }: { row: SpreadRow }) {
  const status = yieldSpreadStatus(row.value);
  return (
    <li className="flex items-center justify-between rounded-lg border border-line p-3">
      <span className="font-medium font-mono">{row.pair}</span>
      <span className={`text-sm font-mono tnum ${status.inverted ? "text-bear font-semibold" : "text-ink"}`}>
        {formatSpread(row.value)}
      </span>
      {status.inverted && (
        <span className="rounded bg-bear/10 px-2 py-0.5 text-xs text-bear">invertiert</span>
      )}
    </li>
  );
}

// Loader-Prop ermöglicht stabilen Aufruf ohne Refetch-Loop.
export function YieldCurveDrilldown({ loader = loadYieldCurve }: { loader?: () => Promise<YieldCurveView> }) {
  const { data, loading, error } = useView(loader);

  // Gesamt-Status: mind. ein Spread negativ → Inversions-Warnung.
  const anyInverted = data?.spreads.some((s) => yieldSpreadStatus(s.value).inverted) ?? false;

  return (
    <DrilldownShell title="Zinskurve (USA)" view={data} loading={loading} error={error}>
      {data && (
        <div className="space-y-6">
          {/* Kurven-Chart: Rendite je Tenor (3M / 2J / 10J / 30J) */}
          <div>
            <h3 className="mb-2 text-sm font-medium text-muted">Renditekurve</h3>
            <LineCurve
              series={[{
                name: "Rendite",
                points: data.points.map((p) => ({ x: p.tenor, y: p.yieldPct })),
              }]}
              height={300}
              area
            />
          </div>

          {/* Spreads: 10J-2J, 10J-3M, 30J-10J — Vorzeichen und Richtung explizit */}
          <div>
            <h3 className="mb-2 text-sm font-medium text-muted">Spreads (Basispunkte)</h3>
            <ul className="space-y-2">
              {data.spreads.map((s) => (
                <SpreadItem key={s.pair} row={s} />
              ))}
            </ul>
          </div>

          {/* Gesamt-Inversions-Status */}
          <div className={`flex items-center gap-2 rounded-lg p-3 text-sm ${anyInverted ? "bg-bear/10 text-bear" : "bg-bull/10 text-bull"}`}>
            <Icon name={anyInverted ? "warning" : "check"} className="h-4 w-4 shrink-0" />
            {anyInverted
              ? "Kurve invertiert → Rezessions-Frühsignal (mind. 1 Spread negativ)"
              : "Kurve nicht invertiert → kein klassisches Rezessions-Frühsignal"}
          </div>
        </div>
      )}
    </DrilldownShell>
  );
}
