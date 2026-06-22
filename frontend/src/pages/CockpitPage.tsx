import { useCockpit, type UseCockpitDeps } from "../hooks/useCockpit";
import { RegimeBanner } from "../components/RegimeBanner";
import { DomainTile } from "../components/DomainTile";
import { DataHealthIndicator } from "../components/DataHealthIndicator";
import { RunControl } from "../components/RunControl";

export function CockpitPage({ deps }: { deps?: UseCockpitDeps }) {
  const { overview, phase, error, startAnalysis } = useCockpit(deps);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold">AAIA — Cockpit</h1>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
        </div>
      </header>

      {phase === "loading" && <p className="text-slate-500">Lädt …</p>}
      {phase === "error" && <p className="text-red-600">{error ?? "Backend nicht erreichbar"}</p>}

      {phase !== "loading" && phase !== "error" && !overview && (
        <p className="text-slate-500">Noch keine Analyse — starte eine über „Analyse starten".</p>
      )}

      {overview && (
        <>
          <RegimeBanner overview={overview} />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overview.domains.map((d) => (
              <DomainTile key={d.key} domain={d} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
