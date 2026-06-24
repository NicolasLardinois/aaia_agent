// BacktestFilters.tsx — Filter-Steuerung fuer den Backtester (US32, Spec §7 Slice 5).
// Kontrollierte Komponente: haelt KEINEN State, meldet nur Aenderungen via onChange.
// Die Optionen (Ticker, underlyings, Regime, Horizonte) werden aus den Roh-Ergebnissen
// abgeleitet und von BacktesterPage uebergeben — keine hardcodierten Listen.
// Vier Filter-Achsen (US32): Ticker, Asset-Klasse (underlying), Regime, Zeitfenster (Horizont).
import type { BacktestFilters as Filters } from "../../lib/backtest";
import type { Underlying } from "../../contract/common";

export interface BacktestFiltersProps {
  // Optionen aus den Roh-Ergebnissen abgeleitet (von BacktesterPage uebergeben).
  tickers: string[];
  underlyings: string[];    // Underlying-Werte als Strings (Asset-Klasse)
  regimes: string[];
  horizons: number[];       // Standardhorizonte 30/60/90 T
  value: Filters;           // aktueller Filter-Zustand (kontrolliert)
  onChange: (patch: Partial<Filters>) => void;  // liefert nur das geaenderte Feld
}

export function BacktestFilters({
  tickers, underlyings, regimes, horizons, value, onChange
}: BacktestFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4">
      {/* Filter 1: Ticker */}
      <div className="flex flex-col gap-1">
        <label htmlFor="bt-filter-ticker" className="text-xs font-medium text-slate-600 dark:text-slate-400">
          Ticker
        </label>
        <select
          id="bt-filter-ticker"
          value={value.ticker ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            // Leerer Wert = "Alle" -> Filter auf dieser Achse zuruecksetzen (undefined = kein Filter)
            onChange({ ticker: v !== "" ? v : undefined });
          }}
          className="rounded border border-slate-200 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">Alle</option>
          {tickers.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Filter 2: Asset-Klasse (underlying) */}
      <div className="flex flex-col gap-1">
        <label htmlFor="bt-filter-underlying" className="text-xs font-medium text-slate-600 dark:text-slate-400">
          Asset-Klasse
        </label>
        <select
          id="bt-filter-underlying"
          value={value.underlying ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            // Leerer Wert = "Alle" -> undefined (kein Filter auf dieser Achse)
            onChange({ underlying: v !== "" ? (v as Underlying) : undefined });
          }}
          className="rounded border border-slate-200 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">Alle</option>
          {underlyings.map((u) => (
            <option key={u} value={u}>{u}</option>
          ))}
        </select>
      </div>

      {/* Filter 3: Regime (Marktphase) */}
      <div className="flex flex-col gap-1">
        <label htmlFor="bt-filter-regime" className="text-xs font-medium text-slate-600 dark:text-slate-400">
          Regime
        </label>
        <select
          id="bt-filter-regime"
          value={value.regime ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            onChange({ regime: v !== "" ? v : undefined });
          }}
          className="rounded border border-slate-200 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">Alle</option>
          {regimes.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* Filter 4: Zeitfenster (Horizont 30/60/90 T = Handelstage, US32) */}
      <div className="flex flex-col gap-1">
        <label htmlFor="bt-filter-horizon" className="text-xs font-medium text-slate-600 dark:text-slate-400">
          Zeitfenster
        </label>
        <select
          id="bt-filter-horizon"
          value={value.horizon ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            // Horizont als number zurueckgeben (30/60/90), nicht als String (US32).
            onChange({ horizon: v !== "" ? (Number(v) as 30 | 60 | 90) : undefined });
          }}
          className="rounded border border-slate-200 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <option value="">Alle</option>
          {horizons.map((h) => (
            // Anzeige "30 T / 60 T / 90 T" (T = Handelstage, US31/US32)
            <option key={h} value={h}>{h} T</option>
          ))}
        </select>
      </div>
    </div>
  );
}
