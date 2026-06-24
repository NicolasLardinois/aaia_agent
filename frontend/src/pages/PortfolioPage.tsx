import { useView } from "../data/useView";
import { loadPortfolio } from "../data/portfolio";
import type { PortfolioView } from "../contract/portfolio";
import { DemoBadge } from "../components/DemoBadge";
import { SourceHealth } from "../components/SourceHealth";
import { ExposurePanel } from "../components/portfolio/ExposurePanel";
import { KlumpenWarnings } from "../components/portfolio/KlumpenWarnings";
import { HedgeSuggestions } from "../components/portfolio/HedgeSuggestions";
import { PositionsTable } from "../components/portfolio/PositionsTable";

// Portfolio-Seite (Track B, US23–27): Risiko-Linse + Positionen. Beratend, KEINE Ausfuehrung.
// Loader-Prop ermoeglicht stabilen Aufruf ohne Refetch-Loop (Modul-Identitaet als Default).
export function PortfolioPage({ loader = loadPortfolio }: { loader?: () => Promise<PortfolioView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Portfolio — Risiko & Positionen (Track B)</h2>
        {data && <DemoBadge isDemo={data.isDemo} />}
        {data && <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />}
      </div>

      {loading && <p className="text-slate-500">Lädt …</p>}
      {!loading && error && <p className="text-red-600">{error}</p>}

      {data && !loading && !error && (
        <>
          <div className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
            <ExposurePanel exposure={data.exposure} />
            <KlumpenWarnings klumpen={data.klumpen} />
            <HedgeSuggestions hedges={data.hedges} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Positionen</h3>
            <PositionsTable positions={data.positions} />
          </div>
        </>
      )}
    </section>
  );
}
