// Portfolio-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern
// denselben Vertrag, PortfolioView extends DemoMeta & SourceHealthMeta. Beta=null bei einer
// Aktien-Position => UNAVAILABLE (Spec §5.4): die Position zaehlt dann NICHT ins net_beta
// (nie als 0 unterstellt). Track B ist beratend — KEINE Trade-Ausfuehrung (US27).
import type {
  DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict,
} from "./common";
import type { SourceHealthMeta } from "./cockpit";

export type Direction = "long" | "short";

// AAIA-Urteil zur Position: beide Linsen, damit die Konflikt-Erkennung die richtige Seite
// gegen die Positionsrichtung prueft (long-Position vs. Long-Verdikt; short vs. Short-Verdikt).
export interface PositionJudgmentDTO {
  longVerdict: LongVerdict;     // BUY/SELL/HOLD/NONE
  shortVerdict: ShortVerdict;   // SHORT/COVER/HOLD/NONE
  confidence: number;           // 0..1 — Konfidenz der relevanten Linse
}

export interface PositionDTO {
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  direction: Direction;
  sizePctNav: number;           // Positionsgroesse in % vom NAV (immer positiv; Vorzeichen kommt aus direction)
  entryPrice: number;           // Einstand in Positionswaehrung
  currency: string;
  sector: string;               // fuer Sektor-Klumpen
  geography: string;            // Land/Region fuer Geographie-Klumpen (z. B. "USA", "Eurozone")
  beta: number | null;          // Aktienmarkt-Beta; null => UNAVAILABLE (nur Aktien/Index relevant)
  judgment: PositionJudgmentDTO;
}

// Exposure-Kennzahlen (US24). net_beta ist AKTIEN-ONLY (vgl. PR #11 / portfolio_monitor_agent):
// Bonds/Rohstoffe/Edelmetalle haben kein Aktienmarkt-Beta. Vola ist datiert (asOf).
export interface ExposureDTO {
  grossPct: number;             // Brutto = Σ|Position| in % NAV
  netPct: number;               // Netto = long − short in % NAV
  netBeta: number;              // beta-gewichtete Aktien-Netto-Exposure in % NAV (aktien-only)
  annualizedVolPct: number | null; // annualisierte Portfolio-Vola in %; null => UNAVAILABLE
  volAsOf: string;              // Stand der Vola-Berechnung (Datierung, PR #11)
}

export type KlumpenDimension = "sector" | "underlying" | "geography";
export interface KlumpenWarningDTO {
  dimension: KlumpenDimension;
  name: string;                 // z. B. "Technologie", "equity", "USA"
  pct: number;                  // Netto-Konzentration |Σsigniert| / Brutto, 0..1
  limit: number;                // greifendes Limit, 0..1
  message: string;              // vorformatierte Warnung, z. B. "Tech 41 % (Limit 30 %)"
}

// Schwellen je Dimension (0..1). Defaults entsprechen portfolio_monitor_agent (PR #11).
export interface ConcentrationLimits {
  sector: number;
  underlying: number;
  geography: number;
}

// Hedge-Vorschlag (US26) — beratend, NIE ausfuehrend (US27).
export interface HedgeSuggestionDTO {
  id: string;
  text: string;                 // konkreter beratender Vorschlag
  rationale: string;            // woraus abgeleitet (Kennzahl/Klumpen)
}

export interface PortfolioView extends DemoMeta, SourceHealthMeta {
  navCurrency: string;          // Basiswaehrung des NAV (z. B. "USD")
  positions: PositionDTO[];
  exposure: ExposureDTO;
  klumpen: KlumpenWarningDTO[];
  hedges: HedgeSuggestionDTO[];
  limits: ConcentrationLimits;  // greifende Limits (fuer Anzeige/Transparenz)
}
