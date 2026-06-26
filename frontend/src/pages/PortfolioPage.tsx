import { useView } from "../data/useView";
import { loadPortfolio } from "../data/portfolio";
import type { PortfolioView } from "../contract/portfolio";
import type { Underlying } from "../contract/common";
import { DemoBadge } from "../components/DemoBadge";
import { SourceHealth } from "../components/SourceHealth";
import { SectionCard } from "../components/SectionCard";
import { ExposurePanel } from "../components/portfolio/ExposurePanel";
import { KlumpenWarnings } from "../components/portfolio/KlumpenWarnings";
import { HedgeSuggestions } from "../components/portfolio/HedgeSuggestions";
import { PositionsTable } from "../components/portfolio/PositionsTable";
import { AllocationBreakdown } from "../components/portfolio/AllocationBreakdown";
import { LongShortBalance } from "../components/portfolio/LongShortBalance";
import { allocationBy, longShortSplit, judgmentAlignment } from "../lib/composition";
import { underlyingToVisual } from "../lib/assets";

// Eine Kennzahl im Ueberblicks-Band (Zahl gross, Label klein) — gibt der Seite sofort "Substanz".
function Kpi({ label, value, tone }: { label: string; value: string; tone?: "bull" | "bear" }) {
  const color = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-ink";
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

// Reicher Inhalts-Block, sobald Daten da sind. Alle Aggregate werden AUS den Positionen
// gerechnet (lib/composition) -> garantiert konsistent zur Tabelle, keine erfundenen Zahlen.
function PortfolioBody({ data }: { data: PortfolioView }) {
  const ls = longShortSplit(data.positions);
  const align = judgmentAlignment(data.positions);
  const byUnderlying = allocationBy(data.positions, "underlying");
  const bySector = allocationBy(data.positions, "sector");
  const byGeography = allocationBy(data.positions, "geography");

  return (
    <>
      {/* Ueberblick — Kennzahlen auf einen Blick + Long/Short-Balance + Exposure-Detail. */}
      <SectionCard eyebrow="Risiko-Linse" title="Überblick" subtitle="Die Lage des Depots in Zahlen">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Kpi label="Positionen" value={String(data.positions.length)} />
          <Kpi label="Brutto" value={`${data.exposure.grossPct} %`} />
          <Kpi
            label="Netto"
            value={`${data.exposure.netPct >= 0 ? "+" : ""}${data.exposure.netPct} %`}
            tone={data.exposure.netPct >= 0 ? "bull" : "bear"}
          />
          <Kpi label="Konflikte" value={String(align.conflict)} tone={align.conflict > 0 ? "bear" : undefined} />
        </div>

        <div className="mt-4">
          <LongShortBalance split={ls} />
        </div>

        <div className="mt-4 border-t border-line pt-4">
          <ExposurePanel exposure={data.exposure} />
        </div>
      </SectionCard>

      {/* Allokation — die VOLLE Verteilung (nicht nur Limit-Ueberschreitungen). */}
      <SectionCard eyebrow="Zusammensetzung" title="Allokation" subtitle="Anteile am gesamten Markt-Engagement">
        <div className="grid gap-5 sm:grid-cols-3">
          <AllocationBreakdown
            title="Asset-Klasse"
            slices={byUnderlying}
            labelFor={(n) => underlyingToVisual(n as Underlying).label}
          />
          <AllocationBreakdown title="Sektor" slices={bySector} />
          <AllocationBreakdown title="Geographie" slices={byGeography} />
        </div>
      </SectionCard>

      {/* Risiko-Hinweise — Klumpen (Grenzwert-Bezug) + beratende Hedge-Vorschlaege. */}
      <SectionCard eyebrow="Aufsicht" title="Risiko-Hinweise" subtitle="Konzentration & Absicherung">
        <div className="space-y-4">
          <KlumpenWarnings klumpen={data.klumpen} />
          <HedgeSuggestions hedges={data.hedges} />
        </div>
      </SectionCard>

      {/* Positionen — mit Einklang-Zusammenfassung darueber. */}
      <SectionCard eyebrow="Bestand" title="Positionen" subtitle={`${align.aligned} von ${align.total} im Einklang mit dem AAIA-Urteil`}>
        <PositionsTable positions={data.positions} />
      </SectionCard>
    </>
  );
}

// Portfolio-Seite (Track B, US23–27): Risiko-Linse + Positionen. Beratend, KEINE Ausfuehrung.
// Loader-Prop ermoeglicht stabilen Aufruf ohne Refetch-Loop (Modul-Identitaet als Default).
export function PortfolioPage({ loader = loadPortfolio }: { loader?: () => Promise<PortfolioView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <section className="space-y-6">
      {/* Hero — Thesis: das Depot als Risiko-Linse, beratend statt ausfuehrend. */}
      <div className="overflow-hidden rounded-panel border border-line bg-surface p-6 shadow-panel">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand">Track B · Risiko-Linse</div>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-3xl font-bold tracking-tight">Portfolio</h2>
          {data && <DemoBadge isDemo={data.isDemo} />}
          {data && <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />}
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Risiko & Positionen auf einen Blick — eine beratende Sicht. AAIA führt keine Trades aus.
        </p>
      </div>

      {loading && <p className="text-muted">Lädt …</p>}
      {!loading && error && <p className="text-bear">{error}</p>}

      {data && !loading && !error && <PortfolioBody data={data} />}
    </section>
  );
}
