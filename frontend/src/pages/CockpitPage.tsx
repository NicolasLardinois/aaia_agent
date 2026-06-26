import { Link } from "react-router-dom";
import { useCockpitContext } from "../hooks/CockpitProvider";
import { RegimeBanner } from "../components/RegimeBanner";
import { RegimeInsightCard } from "../components/RegimeInsightCard";
import { MarketPulse } from "../components/MarketPulse";
import { DomainTile } from "../components/DomainTile";
import { DataHealthIndicator } from "../components/DataHealthIndicator";
import { RunControl } from "../components/RunControl";
import { Icon } from "../components/icons";
import { LoadingExperience } from "../components/loading/LoadingExperience";

// Liest den Lauf-Zustand aus dem CockpitProvider (oberhalb der Routen), damit ein
// laufender Lauf beim Wegnavigieren nicht abbricht (Bug #5/#7).
export function CockpitPage() {
  const { overview, phase, error, startAnalysis, events } = useCockpitContext();

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cockpit — Übersicht</h2>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
        </div>
      </div>

      {/* Lade-Erlebnis (#3): Hexagon-Spinner + rotierende Boersenweisheiten — beim ersten
          Seitenaufbau und waehrend des laufenden Mehr-Agenten-Laufs (mit Live-Schrittzahl). */}
      {phase === "loading" && <LoadingExperience title="Cockpit wird geladen" />}
      {phase === "running" && <LoadingExperience events={events} />}
      {phase === "error" && <p className="text-bear">{error ?? "Backend nicht erreichbar"}</p>}
      {phase === "ready" && !overview && (
        <p className="text-muted">Noch keine Analyse — starte eine über „Analyse starten".</p>
      )}

      {/* Ergebnis-Kacheln nur, wenn kein Lauf laeuft — sonst zeigt das Lade-Erlebnis,
          dass gerade gearbeitet wird (keine veralteten Werte waehrend des Laufs). */}
      {overview && phase !== "running" && phase !== "loading" && (
        <>
          {/* Regime-Banner: klickbar -> Makro-Drilldown (B7) — die Headline der Seite. */}
          <Link to="/cockpit/macro" className="block hover:opacity-90 transition-opacity">
            <RegimeBanner overview={overview} />
          </Link>

          {/* Deutungs-Reihe (#4 "Cockpit zu leer"): Markt-Puls verdichtet die Domaenen-
              Signale, die Regime-Deutung erklaert die Phase. Bei fehlenden Makro-Daten
              entfaellt die Deutung und der Markt-Puls nimmt die volle Breite ein. */}
          <div className={`grid gap-3 ${overview.macro_status === "available" ? "md:grid-cols-2" : ""}`}>
            <MarketPulse domains={overview.domains} />
            {overview.macro_status === "available" && <RegimeInsightCard regime={overview.regime} />}
          </div>

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
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-line p-3 text-center text-sm font-medium
                         text-ink transition-colors hover:border-brand/40 hover:bg-surface-2"
            >
              Buffett-Indikator
              <Icon name="arrow-right" className="h-4 w-4" />
            </Link>
            <Link
              to="/cockpit/big-mac"
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-line p-3 text-center text-sm font-medium
                         text-ink transition-colors hover:border-brand/40 hover:bg-surface-2"
            >
              Big-Mac-Index
              <Icon name="arrow-right" className="h-4 w-4" />
            </Link>
          </div>
        </>
      )}
    </section>
  );
}
