import type { ReactNode } from "react";
import type { ExposureDTO } from "../../contract/portfolio";
import { UnavailableField } from "../UnavailableField";

function Metric({ label, value, definition }: { label: string; value: ReactNode; definition: string }) {
  return (
    <div className="flex-1 rounded-lg border border-line p-3">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="text-xl font-bold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-muted">{definition}</div>
    </div>
  );
}

// Exposure-Panel (US24, Wireframe §4.8): Brutto/Netto/net_beta je mit kurzer Inline-Definition
// (PM evtl. nicht jargon-fest). net_beta ist PFLICHT als "aktien-only" gekennzeichnet (PR #11),
// mit datierter Vola. Brutto = Σ|Position|, Netto = long − short.
export function ExposurePanel({ exposure }: { exposure: ExposureDTO }) {
  const net = `${exposure.netPct >= 0 ? "+" : ""}${exposure.netPct} %`;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-3">
        <Metric label="Brutto-Exposure" value={`${exposure.grossPct} %`} definition="Σ|Position| — gesamtes Markt-Engagement" />
        <Metric label="Netto-Exposure" value={net} definition="long − short — Netto-Marktrichtung" />
        <Metric
          label="net_beta (aktien-only)"
          // null => UNAVAILABLE statt "0 %": 0 wuerde faelschlich "marktneutral" suggerieren,
          // obwohl der Wert mangels Aktien-Beta schlicht unbekannt ist (AGENTS.md §3).
          value={exposure.netBeta === null
            ? <UnavailableField reason="net_beta nicht verfügbar (kein Aktien-Beta)" />
            : `${exposure.netBeta} %`}
          definition="beta-gewichtetes Aktien-Netto — Marktsensitivität (nur Aktien/Index)"
        />
      </div>
      <div className="text-xs text-muted">
        Annualisierte Portfolio-Vola:{" "}
        {exposure.annualizedVolPct === null
          ? <UnavailableField reason="Vola nicht verfügbar" />
          : <span className="font-medium">{exposure.annualizedVolPct} % (Stand {exposure.volAsOf})</span>}
      </div>
    </div>
  );
}
