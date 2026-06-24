import { useView } from "../../data/useView";
import { loadMacro } from "../../data/cockpit";
import { inflationBand } from "../../lib/inflation";
import { SignalBadge } from "../../components/SignalBadge";
import { UnavailableField } from "../../components/UnavailableField";
import { DrilldownShell } from "./DrilldownShell";
import type { MacroView, InflationRow } from "../../contract/cockpit";

// Band-Beschreibung fuer den UI-Nutzer (Zusatzinfo pro Band).
function bandDescription(band: string): string {
  switch (band) {
    case "deflation": return "Deflation — belastet nominale Gewinne";
    case "below":     return "Unter Ziel — expansiver Spielraum";
    case "target":    return "Zielzone — stützt Wachstum";
    case "elevated":  return "Erhöht — bremst Konsum / Bewertungen";
    case "high":      return "Hoch — klarer Bremseffekt";
    default:          return "";
  }
}

function InflationRow({ row }: { row: InflationRow }) {
  const band = inflationBand(row.cpiPct, row.region);
  return (
    <tr className="border-t border-slate-100">
      <td className="py-2 pr-4 font-medium">{row.region}</td>
      <td className="py-2 pr-4">
        {row.cpiPct !== null ? `${row.cpiPct} %` : "—"}
      </td>
      <td className="py-2 pr-4">
        {row.signal !== null
          ? <SignalBadge signal={row.signal} />
          : <UnavailableField reason="CPI-Daten nicht verfügbar" />}
      </td>
      <td className="py-2 pr-4 text-xs text-slate-600">
        {band.activeThreshold}
        {band.band !== "unavailable" && (
          <span className="ml-1 text-slate-400">— {bandDescription(band.band)}</span>
        )}
      </td>
      <td className="py-2 text-xs text-slate-400">{row.dataDate}</td>
    </tr>
  );
}

// Loader-Prop erlaubt stabile Übergabe (kein Refetch-Loop via inline-Arrow).
export function MacroDrilldown({ loader = loadMacro }: { loader?: () => Promise<MacroView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <DrilldownShell title="Makro — Inflation" view={data} loading={loading} error={error}>
      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-2 pr-4">Region</th>
                <th className="pb-2 pr-4">CPI YoY</th>
                <th className="pb-2 pr-4">Signal</th>
                <th className="pb-2 pr-4">Greifende Schwelle</th>
                <th className="pb-2">Stand</th>
              </tr>
            </thead>
            <tbody>
              {data.inflation.map((row) => (
                <InflationRow key={row.region} row={row} />
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-400">
            Regionen: USA und DE nutzen Eurozone-Schwellen (Zielzone 1–3 %); CH hat strukturell
            niedrigere Inflation (Zielzone 0,5–2 %). Keine „EU"-Aggregation (länderspezifisch).
          </p>
        </div>
      )}
    </DrilldownShell>
  );
}
