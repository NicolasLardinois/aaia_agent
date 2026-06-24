import { Link } from "react-router-dom";
import { useCockpit, type UseCockpitDeps } from "../hooks/useCockpit";
import { RegimeBanner } from "../components/RegimeBanner";
import { DomainTile } from "../components/DomainTile";
import { DataHealthIndicator } from "../components/DataHealthIndicator";
import { RunControl } from "../components/RunControl";

export function CockpitPage({ deps }: { deps?: UseCockpitDeps }) {
  const { overview, phase, error, startAnalysis } = useCockpit(deps);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cockpit — Übersicht</h2>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
        </div>
      </div>

      {phase === "loading" && <p className="text-slate-500">Lädt …</p>}
      {phase === "error" && <p className="text-red-600">{error ?? "Backend nicht erreichbar"}</p>}
      {phase !== "loading" && phase !== "error" && phase !== "running" && !overview && (
        <p className="text-slate-500">Noch keine Analyse — starte eine über „Analyse starten".</p>
      )}

      {overview && (
        <>
          {/* Regime-Banner: klickbar -> Makro-Drilldown (B7) */}
          <Link to="/cockpit/macro" className="block hover:opacity-90 transition-opacity">
            <RegimeBanner overview={overview} />
          </Link>

          {/* Domain-Kacheln: jede verlinkt auf ihren Drilldown (B7, DomainTile ist jetzt ein Link) */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overview.domains.map((d) => (
              <DomainTile key={d.key} domain={d} />
            ))}
          </div>

          {/* Schnellzugriff Buffett-Indikator + Big-Mac-Index (B7, Dispatch C füllt die Seiten) */}
          <div className="flex gap-3">
            <Link
              to="/cockpit/buffett"
              className="flex-1 rounded-lg border border-slate-200 p-3 text-center text-sm font-medium
                         text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              Buffett-Indikator →
            </Link>
            <Link
              to="/cockpit/big-mac"
              className="flex-1 rounded-lg border border-slate-200 p-3 text-center text-sm font-medium
                         text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              Big-Mac-Index →
            </Link>
          </div>
        </>
      )}
    </section>
  );
}
