import { Link } from "react-router-dom";
import type { CockpitWindDTO } from "../../contract/deepdive";
import { SignalBadge } from "../SignalBadge";

// Cockpit-Signal als Ruecken-/Gegenwind im Deep-Dive + Rueck-Link ins Drilldown (US12, Konzept §3).
export function CockpitWind({ wind }: { wind: CockpitWindDTO }) {
  return (
    <div className="rounded-lg border border-line p-3 text-sm">
      <div className="text-xs uppercase tracking-wide text-muted">Cockpit-Rücken-/Gegenwind</div>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <span className="font-medium">{wind.domainLabel}:</span>
        <SignalBadge signal={wind.signal} />
        <Link to={`/cockpit/${wind.domainKey}`} className="text-brand underline">
          ↗ ins Cockpit-Drilldown
        </Link>
      </div>
      <p className="mt-1 text-muted">{wind.note}</p>
    </div>
  );
}
