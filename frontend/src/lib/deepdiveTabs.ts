import type { DeepDiveView } from "../contract/deepdive";

// Tab-Registry je underlying (Spec §7-Slice-2-Zeile, Konzept §4.5: Tab-Set kontextabhaengig).
// equity != bond != index != commodity. Futures-Tab nur bei wrapper=future. Backtest immer zuletzt.
export type TabKey =
  | "valuation" | "quality" | "signals"
  | "bond" | "index" | "commodity"
  | "futures" | "backtest";

export interface TabDef { key: TabKey; label: string; }

const BY_UNDERLYING: Record<DeepDiveView["underlying"], TabDef[]> = {
  equity: [
    { key: "valuation", label: "Bewertung" },
    { key: "quality", label: "Qualität" },
    { key: "signals", label: "Signale" },
  ],
  bond: [{ key: "bond", label: "Anleihe" }],
  equity_index: [{ key: "index", label: "Index" }],
  commodity: [{ key: "commodity", label: "Rohstoff" }],
  precious_metal: [{ key: "commodity", label: "Edelmetall" }],
};

export function tabsFor(view: DeepDiveView): TabDef[] {
  if (!view.found) return [];
  const tabs = [...BY_UNDERLYING[view.underlying]];
  if (view.wrapper === "future") tabs.push({ key: "futures", label: "Futures" });
  tabs.push({ key: "backtest", label: "Backtest-Kontext" });
  return tabs;
}
