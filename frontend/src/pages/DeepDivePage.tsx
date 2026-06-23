import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import { useView } from "../data/useView";
import { loadDeepDive } from "../data/deepdive";
import { tabsFor, type TabKey } from "../lib/deepdiveTabs";
import type { DeepDiveView } from "../contract/deepdive";
import { DeepDiveHeader } from "../components/deepdive/DeepDiveHeader";
import { CockpitWind } from "../components/deepdive/CockpitWind";
import { LongShortPanel } from "../components/LongShortPanel";
import { AnomalyReport } from "../components/AnomalyReport";
import { SourceHealth } from "../components/SourceHealth";
import { DemoBadge } from "../components/DemoBadge";
import { EquityTabs } from "../components/deepdive/tabs/EquityTabs";
import { BondTab } from "../components/deepdive/tabs/BondTab";
import { IndexTab } from "../components/deepdive/tabs/IndexTab";
import { CommodityTab } from "../components/deepdive/tabs/CommodityTab";
import { BacktestContextTab } from "../components/deepdive/tabs/BacktestContextTab";
import { FuturesTab } from "../components/deepdive/tabs/FuturesTab";

// Tab-Inhalte kapseln den Switch — alle kontextabhaengigen Tabs je underlying + Futures (wrapper=future).
function TabContent({ tab, view }: { tab: TabKey; view: DeepDiveView }) {
  switch (tab) {
    case "valuation": return <EquityTabs block={view.equity!} tab="valuation" />;
    case "quality":   return <EquityTabs block={view.equity!} tab="quality" />;
    case "signals":   return <EquityTabs block={view.equity!} tab="signals" />;
    case "bond":      return <BondTab block={view.bond!} />;
    case "index":     return <IndexTab block={view.index!} />;
    case "commodity": return <CommodityTab block={view.commodity!} />;
    case "futures":   return <FuturesTab block={view.futures!} />;
    case "backtest":  return <BacktestContextTab ctx={view.backtestContext!} />;
    default:          return null;
  }
}

// Deep-Dive pro Anlage (US10, 17, 18–22): laedt per :ticker ueber die Tausch-Naht.
// Tabs kontextabhaengig je underlying (equity/bond/index/commodity); Futures-Tab nur bei wrapper=future.
// loader-Prop mit Default-Modul-Funktion -> stabile Referenz -> kein Refetch-Loop (wie YieldCurveDrilldown).
export function DeepDivePage({
  loader = loadDeepDive,
}: {
  loader?: (ticker: string) => Promise<DeepDiveView>;
}) {
  const { ticker = "" } = useParams();
  const load = useCallback(() => loader(ticker), [loader, ticker]);
  const { data, loading, error } = useView(load);
  const [active, setActive] = useState<TabKey | null>(null);

  if (loading) return <p className="text-slate-500">Lädt …</p>;
  if (error || !data) return <p className="text-red-600">{error ?? "Keine Daten"}</p>;

  if (!data.found) {
    return (
      <div className="space-y-2">
        <DeepDiveHeader view={data} />
        <p className="text-slate-600">
          Ticker „{data.ticker}" nicht gefunden. Bitte anderen Ticker suchen.
        </p>
      </div>
    );
  }

  const tabs = tabsFor(data);
  const current = active ?? tabs[0]?.key ?? null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <DeepDiveHeader view={data} />
        <DemoBadge isDemo={data.isDemo} />
      </div>
      <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />
      <LongShortPanel long={data.long} short={data.short} />
      <AnomalyReport anomaly={data.anomaly} />
      {data.cockpitWind && <CockpitWind wind={data.cockpitWind} />}

      {/* Tab-Leiste aus Registry — je underlying unterschiedliche Tabs */}
      <div role="tablist" className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={t.key === current}
            onClick={() => setActive(t.key)}
            className={`px-3 py-1.5 text-sm ${
              t.key === current ? "border-b-2 border-sky-500 font-medium" : "text-slate-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {current && <div className="pt-2">{<TabContent tab={current} view={data} />}</div>}
    </section>
  );
}
