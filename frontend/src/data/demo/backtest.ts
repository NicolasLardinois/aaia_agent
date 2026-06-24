// frontend/src/data/demo/backtest.ts
// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Roh-Ergebnisse quer ueber Bereich x Ticker x underlying x Regime x Horizont; die Bereichs-
// Aggregate werden AUS den Roh-Ergebnissen berechnet (eine Quelle der Wahrheit) -> Karten &
// Filterzahlen driften nicht auseinander (gleiches Prinzip wie demoPortfolio).
// Regime-Namen folgen der Cockpit-Demo (deutsche Phasen, hier gross geschrieben: AUFSCHWUNG etc.).
import type { BacktestView, BacktestResult, BacktestArea } from "../../contract/backtest";
import { filterResults, hitRate } from "../../lib/backtest";

const RESULTS: BacktestResult[] = [
  // --- TOP-DOWN: war das Regime korrekt? (ueber die Horizonte) ---
  // 3 von 4 korrekt = 75 % Trefferquote fuer top_down (realistisch nicht-perfekt)
  { id: "td-1", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-01-06" },
  { id: "td-2", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "AUFSCHWUNG", horizon: 60, correct: true,  timestamp: "2026-01-20" },
  { id: "td-3", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "ABSCHWUNG",  horizon: 90, correct: false, timestamp: "2026-02-10" },
  { id: "td-4", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "ABSCHWUNG",  horizon: 30, correct: true,  timestamp: "2026-03-03" },
  // --- BOTTOM-UP: war das dominante Signal korrekt? ---
  // 3 von 4 korrekt = 75 % Trefferquote fuer bottom_up
  { id: "bu-1", area: "bottom_up", ticker: "AAPL", underlying: "equity",         regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-01-13" },
  { id: "bu-2", area: "bottom_up", ticker: "GC=F", underlying: "precious_metal", regime: "AUFSCHWUNG", horizon: 60, correct: false, timestamp: "2026-02-17" },
  { id: "bu-3", area: "bottom_up", ticker: "TLT",  underlying: "bond",           regime: "REZESSION",  horizon: 90, correct: true,  timestamp: "2026-03-24" },
  { id: "bu-4", area: "bottom_up", ticker: "AAPL", underlying: "equity",         regime: "ABSCHWUNG",  horizon: 30, correct: true,  timestamp: "2026-04-07" },
  // --- JUDGMENT: war das Urteil profitabel? ---
  // 3 von 4 korrekt = 75 % Trefferquote fuer judgment
  { id: "ju-1", area: "judgment", ticker: "AAPL", underlying: "equity",         regime: "AUFSCHWUNG", horizon: 60, correct: true,  timestamp: "2026-01-27" },
  { id: "ju-2", area: "judgment", ticker: "XLE",  underlying: "equity",         regime: "ABSCHWUNG",  horizon: 90, correct: false, timestamp: "2026-02-24" },
  { id: "ju-3", area: "judgment", ticker: "GC=F", underlying: "precious_metal", regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-03-17" },
  { id: "ju-4", area: "judgment", ticker: "TLT",  underlying: "bond",           regime: "REZESSION",  horizon: 60, correct: true,  timestamp: "2026-04-14" },
];

const AREAS: BacktestArea[] = ["top_down", "bottom_up", "judgment"];

export function demoBacktest(): BacktestView {
  // Bereichs-Aggregate AUS den Roh-Ergebnissen ableiten (keine handgesetzten Zahlen).
  // So ist garantiert, dass Karten-Vorschau und gefilterte Roh-Ergebnisse immer konsistent sind.
  const areas = AREAS.map((area) => {
    const hr = hitRate(filterResults(RESULTS, { area }));
    return { area, hitRatePct: hr.rate, sampleSize: hr.n };
  });
  return {
    isDemo: true,
    sourcesActive: 2,
    sourcesTotal: 3,
    // Bewusst eine ausgefallene Quelle -> UNAVAILABLE-Pfad sichtbar (Spec §1/§5.4).
    // Vollstaendige Kurs-Historien sind noch nicht angebunden; Demo nutzt synthetische Calls.
    failed: [{ key: "Historien-Feed (Stub)", reason: "Vollstaendige Kurs-Historie noch nicht angebunden" }],
    results: RESULTS,
    areas,
  };
}
