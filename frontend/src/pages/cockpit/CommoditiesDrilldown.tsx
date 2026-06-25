import { useView } from "../../data/useView";
import { loadCommodities } from "../../data/cockpit";
import { SignalBadge } from "../../components/SignalBadge";
import { UnavailableField } from "../../components/UnavailableField";
import { DrilldownShell } from "./DrilldownShell";
import type { CommoditiesView } from "../../contract/cockpit";

// Loader-Prop ermöglicht stabilen Aufruf ohne Refetch-Loop.
export function CommoditiesDrilldown({ loader = loadCommodities }: { loader?: () => Promise<CommoditiesView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <DrilldownShell title="Rohstoffe" view={data} loading={loading} error={error}>
      {data && (
        <ul className="space-y-3">
          {data.commodities.map((c) => (
            <li key={c.ticker} className="rounded-lg border border-line p-3">
              <div className="flex items-center justify-between">
                <span className="font-medium">{c.name}</span>
                <span className="text-xs text-muted">{c.ticker}</span>
                {c.signal !== null
                  ? <SignalBadge signal={c.signal} />
                  : <UnavailableField reason="Datenquelle nicht verfügbar" />}
              </div>
              {c.note && <p className="mt-1 text-xs text-muted">{c.note}</p>}
            </li>
          ))}
        </ul>
      )}
    </DrilldownShell>
  );
}
