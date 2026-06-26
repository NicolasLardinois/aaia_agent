// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Mehrere Ticker quer ueber underlying x wrapper; unbekannt -> "nicht gefunden"-View.
import type { DeepDiveView } from "../../contract/deepdive";
import type { LongVerdict, ShortVerdict } from "../../contract/common";

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
      // Erweiterter Kennzahlen-Katalog (B1). pegRatio bewusst null -> "n.v."-Pfad.
      fundamentals: {
        forwardPe: 28.2, shillerCape: 34.0, pegRatio: null, evRevenue: 8.1,
        priceBook: 46.0, priceSales: 8.3, priceFcf: 30.0, dividendYieldPct: 0.5,
        waccPct: 8.4, revenueCagr3yPct: 8.0, debtToEquity: 1.5,
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

// --- Generische Aktien-Fixtures (Bug #10: groesseres Such-Universum) ---
// Bewusst kompakter Generator: jede bekannte Aktie aus dem TICKER_UNIVERSE soll als
// Demo-Deep-Dive oeffnen, statt "nicht gefunden" zu zeigen. Zahlen sind plausible
// Demo-Ballparks (isDemo:true -> DemoBadge), keine exakten Echtwerte.
interface EquityProfile {
  ticker: string;
  name: string;
  market: string;
  price: number;
  sector: string;          // steuert Altman-Z-Schwellen (Original vs. Z'')
  pe: number;              // KGV
  evEbitda: number;
  grossMarginPct: number;
  operatingMarginPct: number;
  roicPct: number;
  altmanZ: number;
  moat: "wide" | "narrow" | "none";
  shortInterestPct: number;
  long: { verdict: LongVerdict; confidence: number; rationale: string; whatFlips: string };
  short: { verdict: ShortVerdict; confidence: number; rationale: string };
  hitRatePct: number;
  sampleSize: number;
}

function equity(p: EquityProfile): () => DeepDiveView {
  return () => ({
    isDemo: true, sourcesActive: 5, sourcesTotal: 5, failed: [],
    ticker: p.ticker, name: p.name, underlying: "equity", wrapper: "single",
    price: p.price, currency: "USD", market: p.market, found: true,
    long: {
      verdict: p.long.verdict, confidence: p.long.confidence, rationale: p.long.rationale,
      xai: {
        drivers: [
          { text: p.moat === "wide" ? "Breiter Burggraben + hohe Kapitalrendite" : "Solide Marktposition", sign: "+" },
          { text: "Kurs im oberen Bereich der Bewertungs-Bandbreite", sign: "-" },
        ],
        conflicts: [], confidenceReason: "ausgewogene Demo-Treiber", whatFlips: p.long.whatFlips,
      },
    },
    short: { verdict: p.short.verdict, confidence: p.short.confidence, rationale: p.short.rationale },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    equity: {
      // Bewertungs-Bandbreiten als +/-Spanne um den Kurs (Demo) — ergibt eine lesbare Bandbreiten-Grafik.
      valuation: {
        methods: [
          { name: "KGV-Multiple", low: Math.round(p.price * 0.90), high: Math.round(p.price * 1.10) },
          { name: "EV/EBITDA-Multiple", low: Math.round(p.price * 0.92), high: Math.round(p.price * 1.12) },
          { name: "DCF", low: Math.round(p.price * 0.85), high: Math.round(p.price * 1.08) },
        ],
        currentPrice: p.price, peRatio: p.pe, evEbitda: p.evEbitda,
      },
      quality: {
        grossMarginPct: p.grossMarginPct, operatingMarginPct: p.operatingMarginPct,
        roicPct: p.roicPct, altmanZ: p.altmanZ, sector: p.sector,
      },
      signals: { shortInterestPct: p.shortInterestPct, insiderSignal: "neutral", earningsTrend: "neutral", moat: p.moat },
    },
    backtestContext: { hitRatePct: p.hitRatePct, sampleSize: p.sampleSize, history: [] },
  });
}

const EQUITY_PROFILES: EquityProfile[] = [
  {
    ticker: "MSFT", name: "Microsoft Corp.", market: "NASDAQ", price: 430, sector: "Technology",
    pe: 35, evEbitda: 25, grossMarginPct: 69, operatingMarginPct: 45, roicPct: 32, altmanZ: 8.5,
    moat: "wide", shortInterestPct: 0.7,
    long: { verdict: "HOLD", confidence: 0.55, rationale: "Cloud-Wachstum stützt die Qualität, Bewertung aber ambitioniert.", whatFlips: "Kursrücksetzer in die Bewertungs-Bandbreite" },
    short: { verdict: "NONE", confidence: 0.16, rationale: "Kein tragfähiger Short — Bilanz erstklassig, kein Katalysator." },
    hitRatePct: 62, sampleSize: 24,
  },
  {
    ticker: "NVDA", name: "NVIDIA Corp.", market: "NASDAQ", price: 125, sector: "Technology",
    pe: 45, evEbitda: 40, grossMarginPct: 75, operatingMarginPct: 55, roicPct: 60, altmanZ: 18,
    moat: "wide", shortInterestPct: 1.2,
    long: { verdict: "HOLD", confidence: 0.50, rationale: "Dominante Marktstellung, aber Bewertung preist viel Wachstum ein.", whatFlips: "Wachstum verlangsamt sich unter die Erwartung" },
    short: { verdict: "NONE", confidence: 0.30, rationale: "Bewertung hoch, aber kein konkreter Katalysator für einen Fall." },
    hitRatePct: 55, sampleSize: 16,
  },
  {
    ticker: "GOOGL", name: "Alphabet Inc.", market: "NASDAQ", price: 178, sector: "Communication Services",
    pe: 24, evEbitda: 16, grossMarginPct: 57, operatingMarginPct: 32, roicPct: 28, altmanZ: 9,
    moat: "wide", shortInterestPct: 0.9,
    long: { verdict: "BUY", confidence: 0.60, rationale: "Werbe-Cashflow + moderate Bewertung im Verhältnis zur Qualität.", whatFlips: "Bewertung läuft der Qualität davon" },
    short: { verdict: "NONE", confidence: 0.15, rationale: "Kein Short — robuste Bilanz, kein Auslöser." },
    hitRatePct: 63, sampleSize: 20,
  },
  {
    ticker: "AMZN", name: "Amazon.com Inc.", market: "NASDAQ", price: 185, sector: "Consumer Discretionary",
    pe: 42, evEbitda: 18, grossMarginPct: 48, operatingMarginPct: 9, roicPct: 14, altmanZ: 5.5,
    moat: "wide", shortInterestPct: 1.1,
    long: { verdict: "HOLD", confidence: 0.54, rationale: "Cloud + Handel stützen, hohes KGV verlangt aber weiteres Margenwachstum.", whatFlips: "Margenausweitung im Cloud-Segment" },
    short: { verdict: "NONE", confidence: 0.20, rationale: "Kein Short — Wachstum und Cashflow intakt." },
    hitRatePct: 59, sampleSize: 19,
  },
  {
    ticker: "TSLA", name: "Tesla Inc.", market: "NASDAQ", price: 250, sector: "Consumer Discretionary",
    pe: 65, evEbitda: 35, grossMarginPct: 18, operatingMarginPct: 9, roicPct: 11, altmanZ: 6.5,
    moat: "narrow", shortInterestPct: 3.0,
    long: { verdict: "HOLD", confidence: 0.45, rationale: "Hohe Bewertung trifft auf Margendruck — Chance/Risiko ausgewogen.", whatFlips: "Margen stabilisieren sich wieder" },
    short: { verdict: "HOLD", confidence: 0.40, rationale: "Short denkbar (Bewertung + Margendruck), aber es fehlt ein klarer Katalysator." },
    hitRatePct: 51, sampleSize: 22,
  },
  {
    ticker: "META", name: "Meta Platforms Inc.", market: "NASDAQ", price: 500, sector: "Communication Services",
    pe: 26, evEbitda: 15, grossMarginPct: 81, operatingMarginPct: 38, roicPct: 30, altmanZ: 8,
    moat: "wide", shortInterestPct: 1.0,
    long: { verdict: "BUY", confidence: 0.59, rationale: "Sehr hohe Marge + moderate Bewertung; Werbe-Cashflow trägt.", whatFlips: "Bewertung läuft der Qualität davon" },
    short: { verdict: "NONE", confidence: 0.17, rationale: "Kein Short — Cashflow stark, kein Auslöser." },
    hitRatePct: 61, sampleSize: 18,
  },
];

const FIXTURES: Record<string, () => DeepDiveView> = {
  AAPL: aapl, "GC=F": gcFuture, TLT: tltBond, SPY: spyIndex, "CL=F": clFuture, "4GLD": goldEtc,
  ...Object.fromEntries(EQUITY_PROFILES.map((p) => [p.ticker, equity(p)])),
};

export function demoDeepDive(ticker: string): DeepDiveView {
  const make = FIXTURES[ticker.toUpperCase()] ?? FIXTURES[ticker];
  return make ? make() : notFound(ticker);
}
