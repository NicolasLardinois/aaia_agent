import { useView } from "../../data/useView";
import { loadSentiment } from "../../data/cockpit";
import { SignalBadge } from "../../components/SignalBadge";
import { UnavailableField } from "../../components/UnavailableField";
import { DrilldownShell } from "./DrilldownShell";
import type { SentimentView } from "../../contract/cockpit";

// Loader-Prop ermöglicht stabilen Aufruf ohne Refetch-Loop.
export function SentimentDrilldown({ loader = loadSentiment }: { loader?: () => Promise<SentimentView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <DrilldownShell title="Sentiment" view={data} loading={loading} error={error}>
      {data && (
        <ul className="space-y-3">
          {data.subSignals.map((s) => (
            <li key={s.name} className="rounded-lg border border-line p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{s.name}</span>
                {s.value !== null && (
                  <span className="rounded bg-surface-2 px-2 py-0.5 text-sm font-mono tnum">
                    {s.value}
                  </span>
                )}
                {s.signal !== null
                  ? <SignalBadge signal={s.signal} />
                  : <UnavailableField reason="Datenquelle nicht verfügbar" />}
              </div>
              {s.note && <p className="mt-1 text-xs text-muted">{s.note}</p>}
            </li>
          ))}
        </ul>
      )}
    </DrilldownShell>
  );
}
