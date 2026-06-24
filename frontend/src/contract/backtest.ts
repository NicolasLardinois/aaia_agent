// frontend/src/contract/backtest.ts
// Backtester-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag, BacktestView extends DemoMeta + SourceHealthMeta. Der Backtester beantwortet rein
// rueckblickend "haetten die alten Calls Geld gebracht" (US31) — er fuehrt KEINE Trades aus.
import type { DemoMeta, Underlying } from "./common";
import type { SourceHealthMeta } from "./cockpit";

// Die drei Analyse-Bereiche (Konzept §2.6, Spec §4.10):
// - top_down  : war das erkannte Marktregime korrekt? (ueber die Horizonte)
// - bottom_up : war das dominante Einzeltitel-Signal korrekt?
// - judgment  : war das Urteil (BUY/SELL/HOLD/SHORT) profitabel?
export type BacktestArea = "top_down" | "bottom_up" | "judgment";

// Zeitfenster/Horizont in Handelstagen — Standardhorizonte des Systems (30/60/90 T, US31/US32).
export type BacktestHorizon = 30 | 60 | 90;

// Marktregime (Großbuchstaben, konsistent zur Cockpit-Demo). Typisiert -> kein Schreibweisen-Drift im Filter.
export type BacktestRegime = "BOOM" | "AUFSCHWUNG" | "ABSCHWUNG" | "REZESSION" | "ERHOLUNG";

// Ein historischer Call = eine Beobachtung im Backtest. `correct` ist die einheitliche
// Erfolgsmetrik je Bereich: Regime korrekt (top_down) / Signal korrekt (bottom_up) /
// Urteil profitabel (judgment). So bleibt die Trefferquote-Mathematik bereichsunabhaengig.
export interface BacktestResult {
  id: string;                 // stabile ID (Bereich+Ticker+Horizont+Datum reicht in der Demo)
  area: BacktestArea;
  ticker: string;             // betroffener Titel/Markt (Filter-Achse, US32)
  underlying: Underlying;     // Asset-Klasse (Filter-Achse, US32)
  regime: BacktestRegime;     // Marktregime zum Zeitpunkt des Calls (Filter-Achse, US32)
  horizon: BacktestHorizon;   // Zeitfenster 30/60/90 T (Filter-Achse, US32)
  correct: boolean;           // war der Call im Nachhinein korrekt/profitabel?
  timestamp: string;          // ISO-Datum des Calls (chronologische Achse fuer die Kurve)
}

// Vorberechnetes Bereichs-Aggregat (fuer die Karten-Vorschau ohne Filter). Wird AUS den
// Roh-Ergebnissen abgeleitet (eine Quelle der Wahrheit) — `hitRatePct:null` => n.v. (n=0).
export interface AreaBacktest {
  area: BacktestArea;
  hitRatePct: number | null;  // Trefferquote in % (0..100); null => leere Stichprobe (UNAVAILABLE != 0)
  sampleSize: number;         // Stichprobengroesse n
}

export interface BacktestView extends DemoMeta, SourceHealthMeta {
  results: BacktestResult[];  // alle Roh-Ergebnisse (Basis fuer Karten + Filter)
  areas: AreaBacktest[];      // vorberechnete Bereichs-Aggregate (ungefiltert), aus results abgeleitet
}
