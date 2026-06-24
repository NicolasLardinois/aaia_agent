import { Link } from "react-router-dom";
import type { CockpitWindDTO } from "../../contract/deepdive";
import { SignalBadge } from "../SignalBadge";

// Cockpit-Signal als Ruecken-/Gegenwind im Deep-Dive + Rueck-Link ins Drilldown (US12, Konzept §3).
export function CockpitWind({ wind }: { wind: CockpitWindDTO }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
      <div className="text-xs uppercase tracking-wide text-slate-500">Cockpit-Rücken-/Gegenwind</div>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <span className="font-medium">{wind.domainLabel}:</span>
        <SignalBadge signal={wind.signal} />
        <Link to={`/cockpit/${wind.domainKey}`} className="text-sky-600 underline">
          ↗ ins Cockpit-Drilldown
        </Link>
      </div>
      <p className="mt-1 text-slate-600 dark:text-slate-300">{wind.note}</p>
    </div>
  );
}
