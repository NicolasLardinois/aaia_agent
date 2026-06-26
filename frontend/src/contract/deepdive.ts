// Deep-Dive-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern
// denselben Vertrag, jeder View extends DemoMeta & SourceHealthMeta. Kontextabhaengige
// Bloecke (equity?/bond?/index?/commodity?) sind optional — genau der zum underlying
// passende Block ist gesetzt. signal=null => UNAVAILABLE (Spec §5.4, nie 0/neutral).
import type {
  DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict, AnomalySeverity,
} from "./common";
import type { SourceHealthMeta } from "./cockpit";
import type { Signal } from "../lib/contract";

// VerdictLens-kompatibel (components/LongShortPanel.tsx): verdict/confidence/rationale/xai.
export interface XaiDriverDTO { text: string; sign: "+" | "-"; }
export interface XaiContentDTO {
  drivers: XaiDriverDTO[];
  conflicts: string[];
  confidenceReason: string;
  whatFlips: string;
}
export interface LongLensDTO {
  verdict: LongVerdict;
  confidence: number;       // 0..1
  rationale: string;
  xai?: XaiContentDTO;
}
export interface ShortLensDTO {
  verdict: ShortVerdict;
  confidence: number;
  rationale: string;
  xai?: XaiContentDTO;
}

// Anomalie am Urteil (AnomalyContent-kompatibel, components/AnomalyReport.tsx).
export interface AnomalyDTO {
  severity: AnomalySeverity;
  outliers: string[];   // statistische Ausreisser |Z|>2.0
  conflicts: string[];  // Signalwidersprueche
}

// --- equity (US13) ---
export interface ValuationMethodDTO { name: string; low: number; high: number; } // je Methode (KGV/EV-EBITDA/DCF)
export interface EquityValuationDTO {
  methods: ValuationMethodDTO[];
  currentPrice: number | null;   // null => UNAVAILABLE
  peRatio: number | null;        // KGV
  evEbitda: number | null;       // EV/EBITDA-Multiple
}
export interface EquityQualityDTO {
  grossMarginPct: number | null;
  operatingMarginPct: number | null;
  roicPct: number | null;
  altmanZ: number | null;        // null => UNAVAILABLE
  sector: string;                // steuert Altman-Z-Schwellen (Original vs. Z'')
}
export interface EquitySignalsDTO {
  shortInterestPct: number | null;   // % der Float leerverkauft
  insiderSignal: Signal | null;      // Netto-Insiderkäufe/-verkäufe
  earningsTrend: Signal | null;      // Earnings-Revisions-Trend
  moat: "wide" | "narrow" | "none" | null; // Buffett-Burggraben
}
// Erweiterter Fundamental-Katalog (US13, Teil-Projekt B1) — spiegelt das Backend-Modell
// FundamentalsSnapshot (snake→camel), damit der spätere Echt-Anschluss 1:1 mappt.
// Optional am EquityBlock: Alt-Fixtures ohne diesen Block bleiben gültig.
export interface EquityFundamentalsDTO {
  forwardPe: number | null;        // KGV auf Basis erwarteter 12M-Gewinne
  shillerCape: number | null;      // zyklisch bereinigtes KGV (10J inflationsbereinigte Gewinne)
  pegRatio: number | null;         // KGV ÷ Gewinnwachstum (≈1 fair)
  evRevenue: number | null;        // Unternehmenswert / Umsatz
  priceBook: number | null;        // KBV
  priceSales: number | null;       // KUV
  priceFcf: number | null;         // Kurs / freier Cashflow
  dividendYieldPct: number | null; // Dividendenrendite in %
  waccPct: number | null;          // gewichtete Kapitalkosten in %
  revenueCagr3yPct: number | null; // Umsatzwachstum p.a. (3J), in %
  debtToEquity: number | null;     // Verschuldungsgrad (Fremd-/Eigenkapital)
}
export interface EquityBlockDTO {
  valuation: EquityValuationDTO;
  quality: EquityQualityDTO;
  signals: EquitySignalsDTO;
  fundamentals?: EquityFundamentalsDTO;
}

// --- bond (US14) ---
export interface BondBlockDTO {
  modifiedDuration: number | null;  // Jahre; null => UNAVAILABLE
  creditRating: string | null;      // z. B. "AA+"
  spreadBps: number | null;         // Spread ggü. risikolos, in Basispunkten
}

// --- index (US15) ---
export interface IndexConstituentDTO { sector: string; weightPct: number; }
export interface IndexBlockDTO {
  valuationPe: number | null;       // KGV des Index
  breadthPct: number | null;        // % Titel über 200-Tage-Linie (Marktbreite)
  momentumSignal: Signal | null;
  composition: IndexConstituentDTO[]; // Sektorgewichte
}

// --- commodity / precious_metal (US16) ---
export interface SeasonalityPointDTO { month: string; avgReturnPct: number; }
export interface CrossMetalRatioDTO { name: string; value: number; note: string; } // z. B. Gold/Silber-Ratio
export interface CommodityBlockDTO {
  supplyDemandSignal: Signal | null;
  supplyDemandNote: string;
  seasonality: SeasonalityPointDTO[];
  cotIndex: number | null;          // 0..100 Perzentil-Rang (konträr: hoch=bearish)
  cotSignal: Signal | null;
  crossMetal: CrossMetalRatioDTO[]; // nur Edelmetalle; sonst []
}

// --- Futures (US33–36, nur wrapper=future) ---
export type CurveFormDTO = "contango" | "backwardation" | "flat";
export interface FuturesCurvePointDTO { contractMonth: string; price: number; } // Spot + Folgemonate
export interface FuturesBlockDTO {
  curve: FuturesCurvePointDTO[];
  form: CurveFormDTO;
  rollYieldAnnualPct: number;       // %/Jahr, Vorzeichen: <0 Contango/Gegenwind, >0 Backwardation
  expiryDate: string;               // Verfall aktueller Kontrakt (ISO)
  nextRollDate: string;             // naechster Roll-Termin (ISO)
  marginInitial: number;            // Initial-Margin in Kontraktwaehrung
  notional: number;                 // Nominalwert (fuer Hebel = notional/margin)
}

// --- Kursverlauf (US13ff, Mangel #6: Kurschart im Deep-Dive) ---
// Tages-Schlusskurse fuer den Sparkline-/Flaechenchart im Kopf der Deep-Dive-Seite.
export interface PricePointDTO { date: string; close: number; } // ISO-Datum + Schlusskurs in `currency`

// --- Cockpit-Rueckenwind (US12) ---
export interface CockpitWindDTO {
  domainKey: string;      // z. B. "commodities" — Ziel des Rueck-Links ins Drilldown
  domainLabel: string;    // z. B. "Rohstoffe (Öl)"
  signal: Signal | null;
  note: string;           // "Öl-Signal stützt die Öl-Aktie" o. ä.
}

// --- Backtest-Kontext (US21) ---
export interface BacktestContextDTO {
  hitRatePct: number | null;   // Trefferquote des Systems fuer diesen Ticker
  sampleSize: number;          // Anzahl historischer Calls
  history: { date: string; verdict: string; correct: boolean }[];
}

export interface DeepDiveView extends DemoMeta, SourceHealthMeta {
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  price: number | null;        // aktueller Kurs; null => UNAVAILABLE
  priceHistory?: PricePointDTO[]; // Tages-Schlusskurse fuer den Kursverlauf-Chart; fehlt => kein Chart
  currency: string;            // z. B. "USD"
  market: string;              // z. B. "NASDAQ", "COMEX"
  found: boolean;              // false => "nicht gefunden"-Ansicht
  long: LongLensDTO;
  short: ShortLensDTO;
  anomaly: AnomalyDTO;
  equity?: EquityBlockDTO;
  bond?: BondBlockDTO;
  index?: IndexBlockDTO;
  commodity?: CommodityBlockDTO;
  futures?: FuturesBlockDTO;   // nur wrapper=future
  cockpitWind?: CockpitWindDTO;
  backtestContext?: BacktestContextDTO;
  // Vergleichsdimensionen (Konzept §5.2): optional, damit bestehende Fixtures unberührt bleiben.
  runningCosts?: string;       // laufende Kosten je Hülle, z. B. "Roll-Kosten (Contango)" / "TER ~0,12 %/Jahr"
  counterpartyRisk?: string;   // Gegenparteirisiko, z. B. "Börse/Clearing" / "physisch hinterlegt"
}
