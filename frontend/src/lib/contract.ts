// TS-Spiegel des Backend-Vertrags (Spec §6). signal ist null bei UNAVAILABLE.
export type Signal = "bullish" | "bearish" | "neutral";
export type Status = "available" | "unavailable";
export type DomainKey = "commodities" | "sentiment" | "yield_curve" | "sectors";

export interface Domain {
  key: DomainKey;
  signal: Signal | null;
  status: Status;
}

export interface CockpitOverview {
  regime: string;
  regime_confidence: number;
  macro_status: Status;
  domains: Domain[];
  sources_active: number;
  sources_total: number;
}
