// Basis-Vertragstypen, die Demo- und Echt-Quellen gemeinsam erfuellen (Spec §2).
// isDemo steuert das DemoBadge automatisch (true=Beispielwerte, false=echt).
export interface DemoMeta {
  isDemo: boolean;
}

export type Underlying = "equity" | "equity_index" | "bond" | "commodity" | "precious_metal";
export type Wrapper = "single" | "fund" | "future" | "physical_etc";

// Long- und Short-Linse sind gleichwertig (Konzept §2.3).
export type LongVerdict = "BUY" | "SELL" | "HOLD" | "NONE";
export type ShortVerdict = "SHORT" | "COVER" | "HOLD" | "NONE";

export type AnomalySeverity = "none" | "low" | "medium" | "high";
