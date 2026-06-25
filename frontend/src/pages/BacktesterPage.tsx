// BacktesterPage.tsx — Backtester-Seite (US31/US32, Spec §7 Slice 5).
// Beantwortet rein rueckblickend "Haetten die alten Calls Geld gebracht?" — KEIN Trade-Execution.
// Drei Karten (Top-Down/Bottom-Up/Judgment) mit je Trefferquote, n, Equity-/Trefferkurve.
// Filter (Ticker/Asset-Klasse/Regime/Horizont) wirken auf alle drei Karten gleichzeitig (US32).
// Loader-Prop = Modul-Identitaet als Default -> kein Refetch-Loop (useView-Invariante).
import { useState } from "react";
import { useView } from "../data/useView";
import { loadBacktest } from "../data/backtest";
import type { BacktestView, BacktestArea } from "../contract/backtest";
import type { BacktestFilters } from "../lib/backtest";
import { filterResults } from "../lib/backtest";
import { DemoBadge } from "../components/DemoBadge";
import { SourceHealth } from "../components/SourceHealth";
import { BacktestCard } from "../components/backtest/BacktestCard";
import { BacktestFilters as BacktestFiltersControl } from "../components/backtest/BacktestFilters";

// Die drei Analyse-Bereiche in Reihenfolge (Wireframe §4.10).
const AREAS: BacktestArea[] = ["top_down", "bottom_up", "judgment"];

export function BacktesterPage({ loader = loadBacktest }: { loader?: () => Promise<BacktestView> }) {
  const { data, loading, error } = useView(loader);

  // Filter-State ohne area (area wird je Karte gesetzt); leerer Anfangszustand = kein Filter.
  const [filters, setFilters] = useState<BacktestFilters>({});

  // Einheitlicher Patch-Handler: aendert nur die explizit gesetzten Felder.
  function handleFilterChange(patch: Partial<BacktestFilters>) {
    setFilters((prev) => ({ ...prev, ...patch }));
  }

  return (
    <section className="space-y-5">
      {/* Seitenkopf mit DemoBadge + SourceHealth */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">
          Backtester — hätten die alten Calls Geld gebracht?
        </h2>
        {data && <DemoBadge isDemo={data.isDemo} />}
        {data && (
          <SourceHealth
            active={data.sourcesActive}
            total={data.sourcesTotal}
            failed={data.failed}
          />
        )}
      </div>

      {/* Lade-/Fehlerzustand */}
      {loading && <p className="text-muted">Lädt …</p>}
      {!loading && error && <p className="text-bear">Fehler: {error}</p>}

      {data && !loading && !error && (
        <>
          {/* Filter-Steuerung (US32): Optionen aus den Roh-Ergebnissen ableiten.
              So passen die Auswahl-Optionen exakt zu den tatsaechlich vorhandenen Daten
              (keine hartkodierten Listen -> konsistente Schreibweise garantiert). */}
          <BacktestFiltersControl
            tickers={[...new Set(data.results.map((r) => r.ticker))].sort()}
            underlyings={[...new Set(data.results.map((r) => r.underlying))].sort()}
            regimes={[...new Set(data.results.map((r) => r.regime))].sort()}
            horizons={[...new Set(data.results.map((r) => r.horizon))].sort((a, b) => a - b)}
            value={filters}
            onChange={handleFilterChange}
          />

          {/* Drei Karten (US31): je Bereich gefilterte Ergebnisse berechnen.
              Der Nutzer-Filter (Ticker/underlying/Regime/Horizont) wirkt auf alle drei Karten.
              Die Karte selbst rechnet hitRate + hitRateCurve ueber die gefilterte Teilmenge.
              Leerer Schnitt -> Karte zeigt "n.v." (nicht 0 %) — UNAVAILABLE != 0. */}
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
            {AREAS.map((area) => {
              // Nutzer-Filter + Bereichs-Filter additiv kombinieren (UND-Verknuepfung).
              const areaResults = filterResults(data.results, { ...filters, area });
              return (
                <BacktestCard key={area} area={area} results={areaResults} />
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
