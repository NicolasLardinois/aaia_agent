import type { EquityBlockDTO } from "../../../contract/deepdive";
import { combineValuationRange, valuationPosition } from "../../../lib/valuationRange";
import { altmanClass } from "../../../lib/altman";
import { formatNumber } from "../../../lib/format";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";
import { SectionCard } from "../../SectionCard";
import { MetricRow } from "../../MetricRow";
import { InfoTip } from "../../InfoTip";

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

// Zahl -> deutscher String für MetricRow (oder null -> "n.v.").
const fmt = (v: number | null): string | null => (v === null ? null : formatNumber(v));

// Kontextabhaengige equity-Tabs (US13): Bewertung/Qualitaet/Signale. Kennzahlen über den
// A-Baukasten (MetricRow/SectionCard/InfoTip) — Erklär-Tooltips + "n.v." (UNAVAILABLE ≠ 0).
// Pure-Logik aus lib/ (Bewertungs-Bandbreite, Altman-Klasse). fundamentals optional (Alt-Fixtures).
export function EquityTabs({ block, tab }: { block: EquityBlockDTO; tab: "valuation" | "quality" | "signals" }) {
  const f = block.fundamentals;

  if (tab === "valuation") {
    const range = combineValuationRange(block.valuation.methods);
    const pos =
      range && block.valuation.currentPrice !== null
        ? valuationPosition(block.valuation.currentPrice, range.low, range.high)
        : null;
    return (
      <div className="space-y-3 text-sm">
        <SectionCard title="Bewertungs-Kennzahlen">
          <MetricRow label="KGV" value={fmt(block.valuation.peRatio)} term="KGV" />
          {f && <MetricRow label="Forward-KGV" value={fmt(f.forwardPe)} term="Forward-KGV" />}
          {f && <MetricRow label="Shiller-CAPE" value={fmt(f.shillerCape)} term="Shiller-CAPE" />}
          {f && <MetricRow label="PEG" value={fmt(f.pegRatio)} term="PEG" />}
          <MetricRow label="EV/EBITDA" value={fmt(block.valuation.evEbitda)} term="EV/EBITDA" />
          {f && <MetricRow label="EV/Umsatz" value={fmt(f.evRevenue)} term="EV/Umsatz" />}
          {f && <MetricRow label="KBV" value={fmt(f.priceBook)} term="KBV" />}
          {f && <MetricRow label="KUV" value={fmt(f.priceSales)} term="KUV" />}
          {f && <MetricRow label="P/FCF" value={fmt(f.priceFcf)} term="P/FCF" />}
          {f && <MetricRow label="Dividendenrendite" value={fmt(f.dividendYieldPct)} unit="%" term="Dividendenrendite" />}
        </SectionCard>

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
      <div className="space-y-3 text-sm">
        <SectionCard title="Profitabilität & Bilanz">
          <MetricRow label="Bruttomarge" value={fmt(block.quality.grossMarginPct)} unit="%" term="Bruttomarge" />
          <MetricRow label="Operative Marge" value={fmt(block.quality.operatingMarginPct)} unit="%" term="Operative Marge" />
          <MetricRow label="ROIC" value={fmt(block.quality.roicPct)} unit="%" term="ROIC" />
          {f && <MetricRow label="WACC" value={fmt(f.waccPct)} unit="%" term="WACC" />}
          {f && <MetricRow label="Umsatzwachstum (3J p.a.)" value={fmt(f.revenueCagr3yPct)} unit="%" term="Umsatzwachstum" />}
          {f && <MetricRow label="Verschuldungsgrad" value={fmt(f.debtToEquity)} term="Verschuldungsgrad" />}
        </SectionCard>

        {/* Altman-Z mit Sektor-Einordnung (eigene Zeile, da Klassen-Label neben dem Wert) */}
        <div className="flex items-center justify-between border-b border-slate-100 py-1.5 last:border-0 dark:border-slate-700/50">
          <span className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
            <span>Altman-Z</span>
            <InfoTip term="Altman-Z" />
          </span>
          <span>
            {num(block.quality.altmanZ)}{" "}
            {cls === "unavailable" ? (
              <UnavailableField reason="Altman-Z nicht verfügbar" />
            ) : (
              <span className="font-medium">({ALTMAN_LABEL[cls]})</span>
            )}
          </span>
        </div>
      </div>
    );
  }

  // signals (Short-Interest / Insider / Earnings-Trend / Moat) — optional mit InfoTip
  return (
    <div className="space-y-2 text-sm">
      <div>Short-Interest: {num(block.signals.shortInterestPct, " %")} <InfoTip term="Short-Interest" /></div>
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
          : <span className="font-medium">{MOAT_LABEL[block.signals.moat]}</span>}{" "}
        <InfoTip term="Moat" />
      </div>
    </div>
  );
}
