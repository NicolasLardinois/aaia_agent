// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Mehrere Ticker quer ueber underlying x wrapper; unbekannt -> "nicht gefunden"-View.
import type { DeepDiveView } from "../../contract/deepdive";

function notFound(ticker: string): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 0, sourcesTotal: 0, failed: [],
    ticker, name: "Unbekannter Titel", underlying: "equity", wrapper: "single",
    price: null, currency: "", market: "", found: false,
    long: { verdict: "NONE", confidence: 0, rationale: "Kein Titel zu diesem Ticker gefunden." },
    short: { verdict: "NONE", confidence: 0, rationale: "Kein Titel zu diesem Ticker gefunden." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
  };
}

function aapl(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 5, sourcesTotal: 6,
    // Bewusst ein ausgefallener Sub-Agent -> UNAVAILABLE-Pfad (Spec §1/§5.4).
    failed: [{ key: "Earnings-Trend (Stub)", reason: "Revisions-Feed noch nicht angebunden" }],
    ticker: "AAPL", name: "Apple Inc.", underlying: "equity", wrapper: "single",
    price: 232.1, currency: "USD", market: "NASDAQ", found: true,
    long: {
      verdict: "HOLD", confidence: 0.58,
      rationale: "Qualität top, aber Bewertung am oberen Rand der Bandbreite.",
      xai: {
        drivers: [
          { text: "Wide Moat + ROIC ~50 % rechtfertigt Prämie", sign: "+" },
          { text: "Kurs über kombinierter Bewertungs-Bandbreite", sign: "-" },
        ],
        conflicts: ["Qualität bullish vs. Bewertung bearish"],
        confidenceReason: "1 Quelle UNAVAILABLE (Earnings-Trend) senkt Konfidenz",
        whatFlips: "Kursrücksetzer in die Bandbreite ODER Margenausweitung",
      },
    },
    short: {
      verdict: "NONE", confidence: 0.18,
      rationale: "Kein tragfähiger Short: Qualität zu hoch, kein Bilanzrisiko.",
    },
    anomaly: { severity: "low", outliers: [], conflicts: ["Qualität vs. Bewertung"] },
    equity: {
      valuation: {
        methods: [
          { name: "KGV-Multiple", low: 170, high: 210 },
          { name: "EV/EBITDA-Multiple", low: 180, high: 220 },
          { name: "DCF", low: 160, high: 205 },
        ],
        currentPrice: 232.1, peRatio: 30.5, evEbitda: 22.4,
      },
      quality: {
        grossMarginPct: 45.2, operatingMarginPct: 30.1, roicPct: 49.8,
        altmanZ: 6.1, sector: "Technology", // Z'' -> safe
      },
      signals: {
        shortInterestPct: 0.8, insiderSignal: "neutral",
        earningsTrend: null,   // UNAVAILABLE (Stub) — NICHT 0/neutral
        moat: "wide",
      },
    },
    backtestContext: {
      hitRatePct: 64, sampleSize: 25,
      history: [
        { date: "2025-09", verdict: "BUY", correct: true },
        { date: "2025-12", verdict: "HOLD", correct: true },
        { date: "2026-03", verdict: "BUY", correct: false },
      ],
    },
  };
}

function gcFuture(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "GC=F", name: "Gold", underlying: "precious_metal", wrapper: "future",
    price: 2380, currency: "USD", market: "COMEX", found: true,
    long: {
      verdict: "HOLD", confidence: 0.47,
      rationale: "Roll-Gegenwind (Contango) bremst Long; Makro stützt.",
      xai: {
        drivers: [
          { text: "Makro-Regime AUFSCHWUNG stützt Edelmetall", sign: "+" },
          { text: "Contango → Roll-Yield −3,1 %/Jahr Gegenwind", sign: "-" },
        ],
        conflicts: ["Top-Down bullish vs. Roll-Struktur bearish"],
        confidenceReason: "Starkes Gegensignal aus der Roll-Struktur",
        whatFlips: "Wechsel in Backwardation ODER Realzins fällt",
      },
    },
    short: { verdict: "NONE", confidence: 0.22, rationale: "Kein tragfähiger Short: Realzins-Druck nicht stark." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    commodity: {
      supplyDemandSignal: "neutral", supplyDemandNote: "Minenangebot stabil, Notenbankkäufe stützen",
      seasonality: [
        { month: "Jan", avgReturnPct: 1.2 }, { month: "Feb", avgReturnPct: 0.4 },
        { month: "Aug", avgReturnPct: 1.8 }, { month: "Sep", avgReturnPct: 2.1 },
      ],
      cotIndex: null, cotSignal: null,  // COT fuer Gold hier UNAVAILABLE (Demo)
      crossMetal: [{ name: "Gold/Silber-Ratio", value: 84, note: "über langfristigem Mittel (~70) → Silber relativ günstig" }],
    },
    futures: {
      curve: [
        { contractMonth: "Spot", price: 2380 },
        { contractMonth: "Jun", price: 2392 },
        { contractMonth: "Sep", price: 2410 },
        { contractMonth: "Dez", price: 2431 },
      ],
      form: "contango",
      rollYieldAnnualPct: -3.1,  // Contango -> negativ (Gegenwind), Konzept §5.1
      expiryDate: "2026-06-26", nextRollDate: "2026-06-26",
      marginInitial: 7150, notional: 238000, // Hebel ~33x
    },
    cockpitWind: {
      domainKey: "commodities", domainLabel: "Rohstoffe (Edelmetall)",
      signal: "neutral", note: "Edelmetall-Treiber im Cockpit aktuell neutral.",
    },
    backtestContext: { hitRatePct: 55, sampleSize: 18, history: [] },
    // Vergleichsdimensionen §5.2: Future = Roll-Kosten (Contango-Gegenwind) + Clearinghouse als Gegenpartei
    runningCosts: "Roll-Kosten (Contango)",
    counterpartyRisk: "Börse/Clearing",
  };
}

function tltBond(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "TLT", name: "20+ Jahre US-Staatsanleihen", underlying: "bond", wrapper: "fund",
    price: 88.4, currency: "USD", market: "NASDAQ", found: true,
    long: {
      verdict: "BUY", confidence: 0.61,
      rationale: "Lange Duration profitiert von erwartet fallenden Zinsen.",
      xai: {
        drivers: [{ text: "Zinswende erwartet → Kursgewinn bei langer Duration", sign: "+" }],
        conflicts: [], confidenceReason: "klares Makro-Signal, geringe Streuung",
        whatFlips: "Inflationsüberraschung nach oben",
      },
    },
    short: { verdict: "NONE", confidence: 0.2, rationale: "Kein Short bei fallender-Zins-Erwartung." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    bond: { modifiedDuration: 16.2, creditRating: "AA+", spreadBps: 5 }, // Treasury: hohe Duration, ~0 Spread
    backtestContext: { hitRatePct: 60, sampleSize: 14, history: [] },
  };
}

function spyIndex(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 4, sourcesTotal: 4, failed: [],
    ticker: "SPY", name: "S&P 500 ETF", underlying: "equity_index", wrapper: "fund",
    price: 542.3, currency: "USD", market: "NYSE Arca", found: true,
    long: {
      verdict: "HOLD", confidence: 0.52,
      rationale: "Breit getragen, aber Bewertung erhöht.",
      xai: {
        drivers: [
          { text: "Breadth 58 % → mehrheitlich über 200-Tage-Linie", sign: "+" },
          { text: "Index-KGV 24 über historischem Schnitt", sign: "-" },
        ],
        conflicts: [], confidenceReason: "ausgewogene Treiber", whatFlips: "Breadth-Verschlechterung < 50 %",
      },
    },
    short: { verdict: "NONE", confidence: 0.25, rationale: "Kein Index-Short im Aufschwung." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    index: {
      valuationPe: 24.1, breadthPct: 58, momentumSignal: "bullish",
      composition: [
        { sector: "Technologie", weightPct: 30 }, { sector: "Finanzen", weightPct: 13 },
        { sector: "Gesundheit", weightPct: 12 }, { sector: "Zyklischer Konsum", weightPct: 11 },
        { sector: "Sonstige", weightPct: 34 },
      ],
    },
    backtestContext: { hitRatePct: 58, sampleSize: 30, history: [] },
  };
}

function clFuture(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 4,
    failed: [{ key: "Saisonalität (Stub)", reason: "historische Monatsrenditen noch nicht angebunden" }],
    ticker: "CL=F", name: "Rohöl WTI", underlying: "commodity", wrapper: "future",
    price: 78.5, currency: "USD", market: "NYMEX", found: true,
    long: {
      verdict: "HOLD", confidence: 0.49,  // <0.50 -> auto-HOLD-Badge sichtbar
      rationale: "Angebotsdisziplin stützt, aber Roll-Gegenwind und COT-Extrem dämpfen.",
      xai: {
        drivers: [
          { text: "OPEC+-Angebotsdisziplin", sign: "+" },
          { text: "COT-Index 72 → Spekulanten stark long (konträr bearish)", sign: "-" },
        ],
        conflicts: ["Fundamental bullish vs. Positionierung bearish"],
        confidenceReason: "Konfidenz <0.50 → auto-HOLD",
        whatFlips: "COT-Entspannung ODER Backwardation",
      },
    },
    short: { verdict: "HOLD", confidence: 0.33, rationale: "Schwacher Short-Ansatz über COT-Extrem." }, // <0.35 -> Cash-Bias
    anomaly: { severity: "medium", outliers: ["COT-Index im 90. Perzentil"], conflicts: ["Fundamental vs. Positionierung"] },
    commodity: {
      supplyDemandSignal: "bullish", supplyDemandNote: "OPEC+ hält Förderung knapp, Nachfrage robust",
      seasonality: [],  // UNAVAILABLE (Stub) — bewusst leer
      cotIndex: 72, cotSignal: "bearish", // konträr: hoher COT-Index -> bearish (wie cot_agent._cot_signal)
      crossMetal: [],
    },
    futures: {
      curve: [
        { contractMonth: "Spot", price: 78.5 },
        { contractMonth: "Aug", price: 78.9 },
        { contractMonth: "Sep", price: 79.4 },
        { contractMonth: "Okt", price: 79.8 },
      ],
      form: "contango", rollYieldAnnualPct: -5.4,
      expiryDate: "2026-07-22", nextRollDate: "2026-07-17",
      marginInitial: 6800, notional: 78500, // Hebel ~11.5x
    },
    cockpitWind: {
      domainKey: "commodities", domainLabel: "Rohstoffe (Öl)",
      signal: "bullish", note: "Öl-Signal aus dem Cockpit stützt die Öl-These (Rückenwind).",
    },
    backtestContext: { hitRatePct: 51, sampleSize: 22, history: [] },
  };
}

function goldEtc(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "4GLD", name: "Xetra-Gold (physisch)", underlying: "precious_metal", wrapper: "physical_etc",
    price: 71.2, currency: "EUR", market: "XETRA", found: true,
    long: {
      verdict: "BUY", confidence: 0.58,  // bewusst BUY (vs. GC=F HOLD) -> Wrapper-Unterschied im Vergleich
      rationale: "Kein Roll-Gegenwind, voll besichert — saubere Gold-Long-Hülle.",
      xai: {
        drivers: [
          { text: "Makro stützt Edelmetall", sign: "+" },
          { text: "Kein Roll-Yield-Gegenwind (physisch)", sign: "+" },
        ],
        conflicts: [], confidenceReason: "keine Roll-Belastung → höhere Konfidenz als Future",
        whatFlips: "Realzins steigt deutlich",
      },
    },
    short: { verdict: "NONE", confidence: 0.2, rationale: "Kein Short auf physisches Gold sinnvoll." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    commodity: {
      supplyDemandSignal: "neutral", supplyDemandNote: "Minenangebot stabil, Notenbankkäufe stützen",
      seasonality: [{ month: "Aug", avgReturnPct: 1.8 }, { month: "Sep", avgReturnPct: 2.1 }],
      cotIndex: null, cotSignal: null,
      crossMetal: [{ name: "Gold/Silber-Ratio", value: 84, note: "über langfristigem Mittel (~70)" }],
    },
    // KEIN futures-Block (physical_etc) — Futures-Tab erscheint nicht.
    backtestContext: { hitRatePct: 57, sampleSize: 12, history: [] },
    // Vergleichsdimensionen §5.2: physisches ETC = laufende TER + vollbesicherte Goldlagerung (kein Gegenparteirisiko im Insolvenzfall)
    runningCosts: "TER ~0,12 %/Jahr",
    counterpartyRisk: "physisch hinterlegt",
  };
}

const FIXTURES: Record<string, () => DeepDiveView> = {
  AAPL: aapl, "GC=F": gcFuture, TLT: tltBond, SPY: spyIndex, "CL=F": clFuture, "4GLD": goldEtc,
};

export function demoDeepDive(ticker: string): DeepDiveView {
  const make = FIXTURES[ticker.toUpperCase()] ?? FIXTURES[ticker];
  return make ? make() : notFound(ticker);
}
