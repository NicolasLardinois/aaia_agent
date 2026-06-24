import type { EquityBlockDTO } from "../../../contract/deepdive";
import { combineValuationRange, valuationPosition } from "../../../lib/valuationRange";
import { altmanClass } from "../../../lib/altman";
import { formatNumber } from "../../../lib/format";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

const ALTMAN_LABEL: Record<string, string> = {
  safe: "solvent",
  grey: "Grauzone",
  distress: "Insolvenzrisiko",
  not_applicable: "nicht anwendbar (Finanzsektor)",
};
const MOAT_LABEL: Record<string, string> = { wide: "breit", narrow: "schmal", none: "keiner" };

function num(v: number | null, suffix = ""): React.ReactNode {
  return v === null ? <UnavailableField /> : <span className="font-medium">{formatNumber(v)}{suffix}</span>;
}

// Kontextabhaengige equity-Tabs (US13): Bewertung/Qualitaet/Signale. Pure-Logik aus lib/.
// UNAVAILABLE-Felder (null) als UnavailableField — nie als 0/neutral (Spec §5.4).
export function EquityTabs({ block, tab }: { block: EquityBlockDTO; tab: "valuation" | "quality" | "signals" }) {
  if (tab === "valuation") {
    const range = combineValuationRange(block.valuation.methods);
    const pos =
      range && block.valuation.currentPrice !== null
        ? valuationPosition(block.valuation.currentPrice, range.low, range.high)
        : null;
    return (
      <div className="space-y-3 text-sm">
        <div>KGV: {num(block.valuation.peRatio)}</div>
        <div>EV/EBITDA: {num(block.valuation.evEbitda)}</div>
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs uppercase text-slate-500">
              <th>Methode</th>
              <th>tief</th>
              <th>hoch</th>
            </tr>
          </thead>
          <tbody>
            {block.valuation.methods.map((m) => (
              <tr key={m.name}>
                <td>{m.name}</td>
                <td>{formatNumber(m.low)}</td>
                <td>{formatNumber(m.high)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {range && (
          <div className="rounded bg-slate-50 p-2 dark:bg-slate-800">
            Kombinierte Bandbreite: <span className="font-medium">{formatNumber(range.low)}–{formatNumber(range.high)}</span>
            {pos && (
              <>
                {" · "}Position:{" "}
                <span className="font-medium">
                  {pos === "undervalued" ? "unterbewertet" : pos === "overvalued" ? "überbewertet" : "fair"}
                </span>
              </>
            )}
            {!pos && <> · Position: nicht verfügbar</>}
          </div>
        )}
      </div>
    );
  }

  if (tab === "quality") {
    const cls = altmanClass(block.quality.altmanZ, block.quality.sector);
    return (
      <div className="space-y-2 text-sm">
        <div>Bruttomarge: {num(block.quality.grossMarginPct, " %")}</div>
        <div>Operative Marge: {num(block.quality.operatingMarginPct, " %")}</div>
        <div>ROIC: {num(block.quality.roicPct, " %")}</div>
        <div>
          Altman-Z: {num(block.quality.altmanZ)}{" "}
          {cls === "unavailable" ? (
            <UnavailableField reason="Altman-Z nicht verfügbar" />
          ) : (
            <span className="font-medium">({ALTMAN_LABEL[cls]})</span>
          )}
        </div>
      </div>
    );
  }

  // signals
  return (
    <div className="space-y-2 text-sm">
      <div>Short-Interest: {num(block.signals.shortInterestPct, " %")}</div>
      <div>Insider: <SignalBadge signal={block.signals.insiderSignal} /></div>
      <div>
        Earnings-Trend:{" "}
        {block.signals.earningsTrend === null
          ? <UnavailableField reason="Earnings-Trend nicht verfügbar" />
          : <SignalBadge signal={block.signals.earningsTrend} />}
      </div>
      <div>
        Moat:{" "}
        {block.signals.moat === null
          ? <UnavailableField />
          : <span className="font-medium">{MOAT_LABEL[block.signals.moat]}</span>}
      </div>
    </div>
  );
}
