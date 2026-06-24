import { anomalySeverityToVisual } from "../lib/anomaly";
import type { AnomalySeverity } from "../contract/common";

export interface AnomalyContent {
  severity: AnomalySeverity;
  outliers: string[];   // statistische Ausreisser |Z|>2.0
  conflicts: string[];  // Signalwidersprueche (Top-Down vs Bottom-Up)
}

// Getrennt: statistische Ausreisser vs. Signalwidersprueche (frontend_notes.md / Konzept §2.3).
export function AnomalyReport({ anomaly }: { anomaly: AnomalyContent }) {
  const v = anomalySeverityToVisual(anomaly.severity);
  return (
    <div className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
      <div>Anomalie-Schwere: <span className={`font-semibold ${v.colorClass}`}>{v.label}</span></div>
      <div className="mt-1"><span className="text-xs uppercase text-slate-500">Statistische Ausreißer: </span>{anomaly.outliers.join("; ") || "—"}</div>
      <div><span className="text-xs uppercase text-slate-500">Signalwidersprüche: </span>{anomaly.conflicts.join("; ") || "—"}</div>
    </div>
  );
}
