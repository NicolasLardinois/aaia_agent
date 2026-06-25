import { useCallback, useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useView } from "../data/useView";
import { loadDeepDive } from "../data/deepdive";
import { tabsFor, type TabKey } from "../lib/deepdiveTabs";
import type { DeepDiveView } from "../contract/deepdive";
import { DeepDiveHeader } from "../components/deepdive/DeepDiveHeader";
import { CockpitWind } from "../components/deepdive/CockpitWind";
import { CompareView } from "../components/deepdive/CompareView";
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

// Default-Gegenstück-Map (Demo): Future <-> physisches Pendant.
// Nur für die Demo-Anzeige; echte Daten liefern eigene Gegenstücke.
const COMPARE_DEFAULT: Record<string, string> = { "GC=F": "4GLD", "4GLD": "GC=F" };

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

// Deep-Dive pro Anlage (US10, 11, 17, 18–22): laedt per :ticker ueber die Tausch-Naht.
// Tabs kontextabhaengig je underlying (equity/bond/index/commodity); Futures-Tab nur bei wrapper=future.
// Vergleichsmodus: ?vergleich=<TICKER> setzt CompareView (US11); onCompare setzt Default-Gegenstueck.
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

  // Vergleichs-Zustand ueber Query-Param (kein eigenes Routing — YAGNI, Plan §C4).
  const [params, setParams] = useSearchParams();
  const compareTicker = params.get("vergleich");
  const [compareView, setCompareView] = useState<DeepDiveView | null>(null);

  useEffect(() => {
    if (!compareTicker) {
      setCompareView(null);
      return;
    }
    let cancelled = false;
    loader(compareTicker).then((v) => {
      if (!cancelled) setCompareView(v);
    });
    return () => { cancelled = true; };
  }, [compareTicker, loader]);

  // Vergleich nur anbieten, wenn es ein sinnvolles Gegenstück desselben Basiswerts gibt
  // (Konzept §5.2/US11). Kein blinder "4GLD"-Fallback mehr — sonst landete man von z. B.
  // AAPL bei einem Gold-ETC (verschiedene underlyings -> sinnloser Vergleich).
  const onCompare = () => {
    const partner = COMPARE_DEFAULT[data?.ticker ?? ""];
    if (partner) setParams({ vergleich: partner });
  };

  if (loading) return <p className="text-muted">Lädt …</p>;
  if (error || !data) return <p className="text-bear">{error ?? "Keine Daten"}</p>;

  if (!data.found) {
    return (
      <div className="space-y-2">
        <DeepDiveHeader view={data} />
        <p className="text-muted">
          Ticker „{data.ticker}" nicht gefunden. Bitte anderen Ticker suchen.
        </p>
      </div>
    );
  }

  const tabs = tabsFor(data);
  // Aktiven Tab gegen die aktuelle Tab-Menge absichern: Bei Ticker-Wechsel (gleiche Komponenten-
  // Instanz, da Route /deep-dive/:ticker erhalten bleibt) kann ein zuvor gewaehlter Tab-Key in der
  // neuen Tab-Menge fehlen (z. B. "quality" von AAPL existiert bei TLT/bond nicht). Ohne diese
  // Absicherung wuerde TabContent einen leeren Block dereferenzieren (Crash). Fallback: erster Tab.
  const current = tabs.some((t) => t.key === active) ? active : (tabs[0]?.key ?? null);

  // Gegenstück für den Vergleich (Demo): nur zeigen, wenn vorhanden (US11, gleicher Basiswert).
  const comparePartner = COMPARE_DEFAULT[data.ticker];

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <DeepDiveHeader view={data} onCompare={comparePartner ? onCompare : undefined} />
        <DemoBadge isDemo={data.isDemo} />
      </div>
      <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />
      <LongShortPanel long={data.long} short={data.short} />
      <AnomalyReport anomaly={data.anomaly} />
      {data.cockpitWind && <CockpitWind wind={data.cockpitWind} />}

      {/* Vergleichsmodus (US11): CompareView wenn ?vergleich= gesetzt */}
      {compareView && (
        <div className="rounded-lg border border-line p-3">
          <div className="mb-2 text-sm font-semibold">Vergleich — gleicher Basiswert, zwei Hüllen</div>
          <CompareView left={data} right={compareView} />
        </div>
      )}

      {/* Tab-Leiste aus Registry — je underlying unterschiedliche Tabs */}
      <div role="tablist" className="flex flex-wrap gap-2 border-b border-line">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={t.key === current}
            onClick={() => setActive(t.key)}
            className={`px-3 py-1.5 text-sm ${
              t.key === current ? "border-b-2 border-brand font-medium" : "text-muted"
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
