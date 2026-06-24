import { useView } from "../../data/useView";
import { loadYieldCurve } from "../../data/cockpit";
import { yieldSpreadStatus } from "../../lib/curve";
import { LineCurve } from "../../components/charts/LineCurve";
import { DrilldownShell } from "./DrilldownShell";
import type { YieldCurveView, SpreadRow } from "../../contract/cockpit";

// Vorzeichen-Formatierung für Spread-Wert (explizit +/− nennen, AGENTS.md §3).
function formatSpread(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)} %-Pkt.`;
}

function SpreadItem({ row }: { row: SpreadRow }) {
  const status = yieldSpreadStatus(row.value);
  return (
    <li className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
      <span className="font-medium font-mono">{row.pair}</span>
      <span className={`text-sm ${status.inverted ? "text-red-600 font-semibold" : "text-slate-700"}`}>
        {formatSpread(row.value)}
      </span>
      {status.inverted && (
        <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">invertiert</span>
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
            <h3 className="mb-2 text-sm font-medium text-slate-600">Renditekurve</h3>
            <LineCurve
              series={[{
                name: "Rendite",
                points: data.points.map((p) => ({ x: p.tenor, y: p.yieldPct })),
              }]}
              height={200}
            />
          </div>

          {/* Spreads: 10J-2J, 10J-3M, 30J-10J — Vorzeichen und Richtung explizit */}
          <div>
            <h3 className="mb-2 text-sm font-medium text-slate-600">Spreads (Basispunkte)</h3>
            <ul className="space-y-2">
              {data.spreads.map((s) => (
                <SpreadItem key={s.pair} row={s} />
              ))}
            </ul>
          </div>

          {/* Gesamt-Inversions-Status */}
          <div className={`rounded-lg p-3 text-sm ${anyInverted ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
            {anyInverted
              ? "⚠ Kurve invertiert → Rezessions-Frühsignal (mind. 1 Spread negativ)"
              : "✓ Kurve nicht invertiert → kein klassisches Rezessions-Frühsignal"}
          </div>
        </div>
      )}
    </DrilldownShell>
  );
}
